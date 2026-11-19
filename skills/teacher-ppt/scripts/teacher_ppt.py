#!/usr/bin/env python3
"""One entry point: catalog, brief/plan gates, native template composition and handoff."""
import argparse,sys,shutil,subprocess,uuid
sys.dont_write_bytecode=True
from pathlib import Path
from common import ROOT,read,write,sha,digest,catalog,need,Blocked,project_path,rel_path
from workflow import brief_issues,binding,review_ok,render_binding,CONTENT_CHECKS,VISUAL_CHECKS
from pptx import inventory,package,Composer,audit

def inv_for(job,plan):
 cat={x['id']:x for x in catalog()['templates']};cache={}
 def get(page):
  if page.get('source_deck'):
   p=project_path(job,page['source_deck']);n=page.get('source_slide')
  else:
   need(page.get('template') in cat,'未知模板id');f=cat[page['template']];p=ROOT/f['file'];n=page.get('template_page');need(sha(p)==f['sha256'],'随包模板发生变化；请用source_deck显式声明修改后的自有模板')
  key=(str(p),n)
  if key not in cache:cache[key]=inventory(p,n)
  return cache[key]
 return get
def ready(job):
 plan=read(Path(job)/'lesson.json');inv=inv_for(job,plan);b=binding(job,plan,inv);return plan,inv,b

def main():
 ap=argparse.ArgumentParser(description=__doc__);sp=ap.add_subparsers(dest='command',required=True)
 p=sp.add_parser('init');p.add_argument('job')
 p=sp.add_parser('catalog');p.add_argument('--query',default='');p.add_argument('--template');p.add_argument('--page',type=int);p.add_argument('--source-deck')
 p=sp.add_parser('check');p.add_argument('job')
 p=sp.add_parser('binding');p.add_argument('job')
 p=sp.add_parser('record-review');p.add_argument('job');p.add_argument('--kind',choices=['content','visual'],required=True);p.add_argument('--input',required=True)
 p=sp.add_parser('build');p.add_argument('job');p.add_argument('--scratch',required=False)
 p=sp.add_parser('render');p.add_argument('job');p.add_argument('--scratch',required=True)
 p=sp.add_parser('register-render');p.add_argument('job');p.add_argument('--images',nargs='+',required=True);p.add_argument('--engine',required=True);p.add_argument('--command-used',required=True)
 p=sp.add_parser('finalize');p.add_argument('job');p.add_argument('--output',required=True)
 p=sp.add_parser('audit');p.add_argument('file')
 args=ap.parse_args();result={}
 if args.command=='init':
  job=Path(args.job).resolve();need(not (job/'brief.json').exists(),'已有任务，直接check恢复，不覆盖需求')
  write(job/'brief.json',{'schema_version':1,'topic':'','audience':'','purpose':'','scope':'full_lesson','extent':{},'constraints':{},'required_points':[],'sources':[],'ambiguities':[],'evidence':{}});result={'job':str(job),'next':'填写brief.json中已知需求；只询问重要歧义，然后check。'}
 elif args.command=='catalog':
  data=catalog()
  if args.source_deck:result=inventory(Path(args.source_deck).resolve(),args.page or 1)
  elif args.template:
   f=next((x for x in data['templates'] if x['id']==args.template),None);need(f is not None,'模板id不存在')
   if args.page:
    result=inventory(ROOT/f['file'],args.page)
    result['template']={'id':f['id'],'name':f['name'],'category':f.get('category',''),'visual_scene':f.get('visual_scene',''),'avoid_for':f.get('avoid_for',[])}
   else:result=f
  else:
   aliases={'一年级':'小学','二年级':'小学','三年级':'小学','四年级':'小学','五年级':'小学','六年级':'小学','小一':'小学','小二':'小学','小三':'小学','小四':'小学','小五':'小学','小六':'小学','七年级':'初中','八年级':'初中','九年级':'初中','初一':'初中','初二':'初中','初三':'初中','高一':'高中','高二':'高中','高三':'高中','大一':'大学','大二':'大学','大三':'大学','大四':'大学','本科':'大学','研究生':'大学','错题':'讲评','习题':'讲评'}
   terms=[]
   for raw in args.query.split():
    w=raw.lower().strip()
    if not w:continue
    for k,v in aliases.items():
     if k in w:
      terms.append(v);w=w.replace(k,'')
    if w:terms.append(w)
   def match(t):
    if not terms:return True
    hay=' '.join([t['id'],t['name'],t.get('category',''),' '.join(t.get('grade_bands',[])),' '.join(t.get('lesson_types',[])),' '.join(t.get('subjects',[])),t.get('visual_scene',''),' '.join(p.get('name','')+' '+p.get('purpose','')+' '+' '.join(p.get('components',[])) for p in t.get('pages',[]))]).lower()
    return all(term in hay for term in terms)
   result={'entry':str(ROOT/'assets/gallery.html'),'templates':[{'id':x['id'],'name':x['name'],'category':x.get('category',''),'grade_bands':x.get('grade_bands',[]),'lesson_types':x.get('lesson_types',[]),'subjects':x.get('subjects',[]),'visual_scene':x.get('visual_scene',''),'avoid_for':x.get('avoid_for',[]),'pages':x['pages'],'preview':str(ROOT/x['preview'])} for x in data['templates'] if match(x)]}
 elif args.command=='audit':result=audit(Path(args.file).resolve())
 else:
  job=Path(args.job).resolve();brief=read(job/'brief.json')
  if args.command=='check':
   issues=brief_issues(brief)
   if issues:result={'stage':'需求定位','status':'needs_clarification','questions':issues}
   elif not (job/'lesson.json').exists():result={'stage':'教学内容','status':'needs_plan','brief_sha256':digest(brief)}
   else:
    plan,inv,b=ready(job)
    try:
     review_ok(job/'content-review.json',b,'content')
     if not (job/'build.json').exists():result={'stage':'课件交付','status':'ready_to_build','flags':b['flags']}
     else:
      build=read(job/'build.json');need(build.get('binding')==b,'候选文件对应旧计划，请重建')
      vb=render_binding(job);review_ok(job/'visual-review.json',vb,'visual');result={'stage':'课件交付','status':'ready_to_finalize','candidate':rel_path(job,project_path(job,build['candidate']))}
    except Blocked as e:result={'stage':'教学内容/课件交付','status':'needs_review_or_build','next':str(e),'flags':b['flags']}
  elif args.command=='binding':
   if (job/'lesson.json').exists():result=ready(job)[2]
   else:result={'brief_sha256':digest(brief)}
  elif args.command=='record-review':
   report=read(args.input);keys=CONTENT_CHECKS if args.kind=='content' else VISUAL_CHECKS
   need(report.get('reviewer') in ['model','human'],'判断结果须来自实际模型或人工检查')
   need(all(k in report.get('checks',{}) for k in keys),'判断项不完整：'+','.join(keys))
   b=ready(job)[2] if args.kind=='content' else render_binding(job)
   report['binding']=b;dest=job/(args.kind+'-review.json');write(dest,report);review_ok(dest,b,args.kind);result={'recorded':str(dest),'note':'此命令仅绑定已有判断，不替模型执行教学或视觉判断。'}
  elif args.command=='build':
   plan,inv,b=ready(job);review_ok(job/'content-review.json',b,'content')
   if args.scratch:
    scratch=Path(args.scratch).resolve()
    need(scratch!=ROOT and ROOT not in scratch.parents,'临时构建不能写入技能目录')
   out=job/'candidate.pptx';tmp_out=job/('.candidate-'+uuid.uuid4().hex[:12]+'.pptx')
   composer=Composer();base=None
   for i,page in enumerate(plan['slides'],1):
    v=inv(page);page=dict(page);page['_facts']=plan.get('facts',[]);source=package(v['path'],v['sha256']);base=source if base is None else base;composer.import_page(v['path'],v['sha256'],v,page,brief,i)
   try:
    composer.save(tmp_out,base);a=audit(tmp_out);need(a['slide_count']==len(plan['slides']),'实际页数不匹配')
    tmp_out.replace(out)
   finally:
    if tmp_out.exists():tmp_out.unlink()
   record={'candidate':rel_path(job,out),'sha256':sha(out),'slide_count':len(plan['slides']),'binding':b,'package_audit':a};write(job/'build.json',record)
   result={'status':'candidate_built','file':str(out),'slide_count':len(plan['slides']),'next':'实际渲染后判断版面；尚未替你判断视觉效果。'}
  elif args.command=='render':
   plan,inv,b=ready(job);build=read(job/'build.json');cand=project_path(job,build['candidate']);need(build['binding']==b and cand.is_file() and sha(cand)==build['sha256'],'候选PPT与当前计划不一致')
   exe=next((shutil.which(x) for x in ['pwsh.exe','pwsh','powershell.exe','powershell'] if shutil.which(x)),None)
   need(exe,'当前PATH未探测到PowerShell；可用实际渲染工具后register-render，不得伪造视觉通过')
   try:subprocess.run([exe,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/render_powerpoint.ps1'),'-Source',str(cand),'-OutputDir',str(job/'previews'),'-Scratch',str(Path(args.scratch).resolve()),'-Report',str(job/'render.json')],check=True)
   except subprocess.CalledProcessError as error:raise Blocked('PowerPoint渲染未通过，请检查render.json中的原始错误或溢出位置') from error
   r=read(job/'render.json');need(r.get('status')=='passed','原生渲染/编辑检查未通过，见render.json');result=r
  elif args.command=='register-render':
   plan,inv,b=ready(job);build=read(job/'build.json');cand=project_path(job,build['candidate']);need(build['binding']==b and cand.is_file() and sha(cand)==build['sha256'],'候选文件已变更')
   need(len(args.images)==len(plan['slides']),'渲染图片须逐页完整且按页序提供')
   pages=[]
   for i,p in enumerate(args.images,1):
    path=project_path(job,p);need(path.is_file(),'渲染图片不存在');need(path.suffix.lower() in ['.png','.jpg','.jpeg','.webp'],'渲染文件应为实际页面图片');pages.append({'slide':i,'file':rel_path(job,path),'sha256':sha(path)})
   result={'status':'passed','pptx_sha256':build['sha256'],'engine':args.engine,'command_used':args.command_used,'pages':pages,'native_edit_probe':'not_performed','native_chart_edit_probe':'not_performed','provenance':'external renderer supplied by executing agent; script verifies binding, not image/PPT visual equivalence'};write(job/'render.json',result)
  elif args.command=='finalize':
   plan,inv,b=ready(job);review_ok(job/'content-review.json',b,'content');build=read(job/'build.json');cand=project_path(job,build['candidate']);need(build['binding']==b and cand.is_file() and sha(cand)==build['sha256'],'候选PPT对应旧计划')
   vb=render_binding(job);review_ok(job/'visual-review.json',vb,'visual')
   out=Path(args.output).resolve();need(not out.exists(),'输出已存在，请用新版本文件名，避免覆盖用户稿');need(ROOT not in out.parents,'不得覆盖技能资源')
   for page in plan['slides']:need(out!=Path(inv(page)['path']),'不得覆盖源课件')
   out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(cand,out);need(sha(out)==build['sha256'],'最终复制哈希不同')
   result={'status':'finalized','file':str(out),'sha256':sha(out),'slide_count':build['slide_count'],'render':rel_path(job,job/'previews'),'native_edit_probe':read(job/'render.json').get('native_edit_probe','not_performed'),'native_chart_edit_probe':read(job/'render.json').get('native_chart_edit_probe','not_applicable')};write(job/'delivery.json',result)
 print(__import__('json').dumps(result,ensure_ascii=False,indent=2))
 if result.get('status')=='needs_clarification':return 2
 return 0

if __name__=='__main__':
 try:sys.exit(main())
 except (Blocked,KeyError,ValueError,TypeError,FileNotFoundError) as e:
  print(__import__('json').dumps({'status':'blocked','reason':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(2)
