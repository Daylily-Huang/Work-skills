"""Deterministic boundaries; pedagogical and visual quality still require real judgment."""
from pathlib import Path
from collections import Counter
import re,math
from common import read,write,digest,sha,project_path,need,Blocked

CONTENT_CHECKS=['focus_and_sequence','age_and_teaching','facts_and_answers','language']
VISUAL_CHECKS=['readability_and_space','illustration_integration','layout_variety','content_matches_plan']
VALID_KINDS={'cover','goal','explain','question','exercise','activity','record','summary','divider','review','edit'}
PLACEHOLDER_RE=re.compile(r'\[(?:填写|待填|课题|课程|课文|本课|单元|授课|学科|课时|学分|结构|主题|学生|答案|判断|推理|结论|记录|用一|用结构|用关系|写下|具体|活动|在这里|理解|表达|核心概念|板书|解题|教学支持|内容与经验|说明核心|课堂小结|提示|示例|目标|任务|问题|材料|方法|观察|观点|理由)[^\]]*\]')
def number(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def load_task(job):return read(Path(job)/'brief.json')
def source_fingerprint(job,brief):
 out=[]
 for s in brief.get('sources',[]):
  need(s.get('id') and s.get('kind') in ['file','url','authored'],'来源必须有id及kind(file/url/authored)')
  need(str(s.get('title','')).strip() and str(s.get('location','')).strip(),f"来源{s.get('id')}须有title和location")
  if s['kind']=='file':
   p=project_path(job,s['location']);need(p.is_file(),f'来源文件不存在：{p}');out.append({'id':s['id'],'sha256':sha(p)})
  else:out.append({'id':s['id'],'record':digest(s)})
 return out

def brief_issues(brief):
 errors=[]
 for k in ['topic','audience','purpose','scope']:
  if not isinstance(brief.get(k),str) or not brief[k].strip():errors.append({'id':'missing.'+k,'question':f'请明确{k}；这会改变教学内容或组织方式。'})
 extent=brief.get('extent',{})
 if not isinstance(extent,dict):return [{'id':'invalid.extent','question':'extent须是包含minutes或slides的对象'}]
 if brief.get('scope') not in ['full_lesson','segment','local_edit']:errors.append({'id':'invalid.scope','question':'任务范围是整节课、一个片段还是局部修改？'})
 if 'slides' in extent and (not isinstance(extent['slides'],int) or isinstance(extent['slides'],bool) or extent['slides']<=0):errors.append({'id':'invalid.slides','question':'页数须为正整数'})
 if 'minutes' in extent and (not number(extent['minutes']) or extent['minutes']<=0):errors.append({'id':'invalid.minutes','question':'授课时长须为正数分钟'})
 if brief.get('scope')=='full_lesson' and not number(extent.get('minutes')):errors.append({'id':'missing.minutes','question':'整节课的授课时长是多少？'})
 if not any(number(extent.get(k)) and extent[k]>0 for k in ['minutes','slides']):errors.append({'id':'missing.extent','question':'请明确时长或页数范围，或记录用户授权你建议的具体值。'})
 if brief.get('constraints',{}).get('textbook_required'):
  book=brief.get('textbook',{})
  if not all(book.get(k) for k in ['edition','volume','unit']):errors.append({'id':'missing.textbook','question':'需要对应的教材版本、册次和单元是什么？'})
 rpts=brief.get('required_points',[])
 rp_ids=[x.get('id') for x in rpts]
 if any(not str(x.get('id','')).strip() or not str(x.get('text','')).strip() for x in rpts):errors.append({'id':'invalid.required_points','question':'每条必讲点须有非空id和text'})
 elif len(rp_ids)!=len(set(rp_ids)):errors.append({'id':'duplicate.required_points','question':'必讲点id重复'})
 for q in brief.get('ambiguities',[]):
  if q.get('status') not in ['answered','delegated'] or (q.get('impact')=='material' and (not str(q.get('answer','')).strip() or not str(q.get('evidence','')).strip())) or not str(q.get('answer','')).strip() or not str(q.get('evidence','')).strip():
   errors.append({'id':q.get('id'),'question':q.get('question'),'reason':'影响内容的重要歧义尚无真实回答或授权依据'})
 ids=[s.get('id') for s in brief.get('sources',[])]
 if len(ids)!=len(set(ids)):errors.append({'id':'duplicate.source','question':'来源id重复'})
 return errors

def check_plan(job,plan,inventory):
 brief=load_task(job);issues=brief_issues(brief);need(not issues,'需求未澄清：'+str(issues))
 sources=source_fingerprint(job,brief)
 need(plan.get('brief_sha256')==digest(brief),'计划未绑定当前brief；先按真实需求更新计划，不能沿用旧绑定')
 local=brief.get('scope')=='local_edit'
 need(local or bool(brief.get('sources')),'非局部修改任务须至少有一项材料来源')
 pages=plan.get('slides',[]);need(pages,'至少需要一页实际内容')
 ids=[s.get('id') for s in pages];need(all(ids) and len(set(ids))==len(ids),'页面id须非空且唯一')
 target=brief.get('extent',{}).get('slides');need(target is None or len(pages)==target,f'页数应为{target}，当前{len(pages)}')
 emphasis=plan.get('emphasis',{})
 need(local or emphasis.get('priorities') and emphasis.get('sequence_reason'),'说明本次侧重及为什么这样组织，不固定套页序')
 goals=plan.get('objectives',[]);gids={g.get('id') for g in goals};need(local or goals,'教学计划需要具体学习目标')
 need(len(gids)==len(goals) and None not in gids,'学习目标id须非空且唯一')
 need(all(g.get('text') for g in goals),'学习目标不能只有id')
 points={x['id'] for x in brief.get('required_points',[])};covered=set();goal_coverage=set();source_ids={s['id'] for s in brief.get('sources',[])}
 raw_facts=plan.get('facts',[]);f_ids=[f.get('id') for f in raw_facts]
 need(all(str(x or '').strip() for x in f_ids) and len(f_ids)==len(set(f_ids)),'事实id须非空且唯一')
 facts={f['id']:f for f in raw_facts}
 flags=[]
 for f in facts.values():
  need(f.get('claim') and f.get('verification',{}).get('method') and f['verification'].get('detail'),f"事实{f['id']}需要核对方法与定位/计算说明")
  f_srcs=f.get('source_ids',[])
  need(f_srcs and set(f_srcs)<=source_ids,f"事实{f['id']}须引用存在的来源")
 for page in pages:
  need(page.get('kind') in VALID_KINDS and str(page.get('intent','')).strip(),f"{page['id']}需要有效页面类型(kind)与教学用途(intent)")
  need(set(page.get('point_ids',[]))<=points,f"{page['id']}引用不存在的必讲点")
  covered.update(page.get('point_ids',[]));goal_coverage.update(page.get('objective_ids',[]))
  need(set(page.get('objective_ids',[]))<=gids,f"{page['id']}引用不存在的学习目标")
  need(set(page.get('fact_ids',[]))<=set(facts),f"{page['id']}引用不存在的事实id")
  inv=inventory(page)
  names={x['field'] for x in inv['text_fields']};bound=set(page.get('text',{}));kept=set(page.get('keep_text',{}))
  need(not bound&kept,f"{page['id']}字段不能同时替换和保留")
  need(bound|kept==names,f"{page['id']}文字字段不完整：未处理{sorted(names-bound-kept)}；不存在{sorted((bound|kept)-names)}")
  need(all(str(v).strip() for v in page.get('keep_text',{}).values()),'保留原字的字段需要说明理由，例如导航标签')
  for k in kept:
   orig=next((x['text'] for x in inv['text_fields'] if x['field']==k),'')
   if len(orig.strip())>12:flags.append({'id':page['id']+':keep:'+k,'page':page['id'],'kind':'kept_long_template_text','excerpt':orig[:30]})
  texts=[]
  for field in inv['text_fields']:
   value=page.get('text',{}).get(field['field'],field['text']);need(isinstance(value,str),'text字段值必须是字符串')
   texts.append(value)
   if field['field'] in page.get('text',{}) and field.get('width_pt') and field.get('max_lines'):
    sz=field.get('font_size_pt') or 18.0;cap=field['width_pt']/sz;ml=field['max_lines'];est=0
    for ln in value.replace('\r\n','\n').replace('\r','\n').split('\n'):
     w=sum(0.58 if ord(ch)<128 else 1.0 for ch in ln)
     est+=max(1,math.ceil(w/(cap*1.05)))
    if (ml==1 and est>=2) or (est>ml+1):
     flags.append({'id':page['id']+':capacity:'+field['field'],'page':page['id'],'kind':'text_capacity_risk','excerpt':f"{field['field']}预计{est}行超出容量{ml}行：{value[:24]}"})
  tables=page.get('tables',[]);need(len(tables)==len(inv['tables']),f"{page['id']}所有原生表格都须显式填写，不能残留样例")
  for spec,base in zip(tables,inv['tables']):
   vals=spec.get('values',[]);need(len(vals)==base['rows'] and all(len(row)==base['columns'] for row in vals),f"{page['id']}表格尺寸需与选定版式一致，换版式或明确修改表格结构")
   texts.extend(str(v) for row in vals for v in row)
  charts=page.get('charts',[]);need(len(charts)==len(inv['charts']),f"{page['id']}所有原生图表都须显式填写")
  for c,base in zip(charts,inv['charts']):
   need(c.get('categories') and len(c.get('series',[]))==base['series_count'],'图表分类/系列数须匹配版式')
   need(c.get('source_id') in source_ids,'图表数据必须对应实际来源；不可沿用模板学情数字')
   for ser in c['series']:
    need(ser.get('name') and len(ser.get('values',[]))==len(c['categories']),'图表系列长度或名称不完整')
    need(all(number(v) for v in ser['values']),'图表需要有限数值，不能猜测截图数值')
   if c.get('illustrative'):need(brief.get('constraints',{}).get('allow_illustrative_data') and '示例' in ''.join(texts),'示意数据须有用户授权，并在该页简短标明“示例”')
  literals=brief.get('constraints',{}).get('allowed_literals',[])
  for t in texts:
   clean=t
   for literal in literals:clean=clean.replace(literal,'')
   need(not PLACEHOLDER_RE.search(clean),f"{page['id']}残留模板替换提示：{t}")
   for bad in ('教材\n图\n片','《课程名称》','版式示例数据'):
    need(bad not in clean,f"{page['id']}残留模板占位词：{bad}")
  copy='\n'.join(texts)
  for term in ['仅供参考','无法保证','请自行核实','作为一个AI','不构成','因人而异']:
   if term in copy:flags.append({'id':page['id']+':copy:'+term,'page':page['id'],'kind':'defensive_copy','excerpt':term})
  if page.get('kind') in ['question','exercise'] and brief.get('constraints',{}).get('answers')!='omit':
   need(page.get('teacher_guidance'),f"{page['id']}需要教师用答案、判断依据或开放题评价要点")
  if page.get('source_ids'):need(set(page['source_ids'])<=source_ids,'页面来源id不存在')
 need(points<=covered,'必讲点未覆盖：'+','.join(sorted(points-covered)))
 need(goal_coverage<=gids and (local or gids<=goal_coverage),'学习目标与实际页面未对应')
 activities=plan.get('activities',[])
 if brief.get('scope')=='full_lesson':
  need(activities,'整节课需有学生实际活动及时间安排')
 if activities:
  a_ids=[a.get('id') for a in activities]
  need(all(str(x or '').strip() for x in a_ids) and len(a_ids)==len(set(a_ids)),'活动id须非空且唯一')
  linked=set()
  for a in activities:
   need(a.get('student_action') and a.get('evidence') and number(a.get('minutes')) and a['minutes']>0,'活动需要学生行为、可观察表现及正数分钟')
   need(set(a.get('slide_ids',[]))<=set(ids) and a.get('slide_ids'),'活动需对应实际页面')
   need(set(a.get('objective_ids',[]))<=gids and a.get('objective_ids'),'活动需对应实际学习目标');linked.update(a['objective_ids'])
  need(brief.get('scope')!='full_lesson' or gids<=linked,'有学习目标未落实到活动')
  if number(brief.get('extent',{}).get('minutes')):
   total_min=sum(a['minutes'] for a in activities)
   need(total_min<=brief['extent']['minutes'],'活动时间总和超过课时')
   if brief.get('scope')=='full_lesson':need(total_min>=0.5*brief['extent']['minutes'],f"整节课活动总时长({total_min}分钟)不足课时({brief['extent']['minutes']}分钟)的一半")
 seq=[(p.get('template'),p.get('template_page'),p.get('source_deck'),p.get('source_slide')) for p in pages]
 seen={seq[0]:0} if seq else {}
 for i in range(1,len(seq)):
  if seq[i]==seq[i-1] and not pages[i].get('repeat_reason'):flags.append({'id':pages[i]['id']+':layout:repeat','page':pages[i]['id'],'kind':'repeated_layout','excerpt':'连续同版式；核对是否适合连续练习/比较，不能仅靠换标题拼页数'})
  elif seq[i] in seen and not pages[i].get('repeat_reason'):flags.append({'id':pages[i]['id']+':layout:nonadjacent_repeat','page':pages[i]['id'],'kind':'repeated_layout','excerpt':'非相邻重复同版式；核对是否适合同类环节呼应，不能拼凑页数'})
  seen.setdefault(seq[i],i)
 if len(seq)>=4 and len(set(seq))<=2 and not any(p.get('repeat_reason') for p in pages):
  flags.append({'id':'deck:layout:alternating','page':'deck','kind':'repeated_layout','excerpt':'全稿>=4页仅交替使用<=2种版式；核对是否因循环套版导致结构单调'})
 templates_used={p.get('template') for p in pages if p.get('template')}
 if len(templates_used)>2 and not any(p.get('style_mix_reason') for p in pages):
  flags.append({'id':'deck:style:mixed','page':'deck','kind':'mixed_styles','excerpt':'单份课件混用超过2套模板风格；核对视觉连贯性是否合理'})
 return {'brief_sha256':digest(brief),'plan_sha256':digest(plan),'sources':sources,'flags':flags}

def binding(job,plan,inventory):
 result=check_plan(job,plan,inventory)
 result['templates']=[list(x) for x in sorted({((p['template'] if p.get('template') else 'source_deck:'+Path(p['source_deck']).name),inventory(p)['sha256']) for p in plan['slides']})]
 return result

def review_ok(path,expected,kind):
 need(Path(path).is_file(),f'缺少{kind}模型判断记录：{path}')
 review=read(path);need(review.get('binding')==expected,'判断记录已过期：需求、计划、来源、模板或渲染发生变化')
 need(review.get('reviewer') in ['model','human'],'需要实际模型或人工判断，脚本不能自判教学/视觉通过')
 required=CONTENT_CHECKS if kind=='content' else VISUAL_CHECKS
 checks=review.get('checks',{})
 for key in required:
  c=checks.get(key,{})
  need(c.get('status') in ['pass','not_applicable'] and str(c.get('reason','')).strip(),f'判断未通过或缺依据：{key}')
 need(not any(x.get('severity')=='blocking' and x.get('status')!='resolved' for x in review.get('findings',[])),'存在未关闭的实质问题')
 flags={x['id'] for x in expected.get('flags',[])}
 need(flags<=set(review.get('flag_decisions',{})),'对检测到的文风/重复版式提示尚无明确判断')
 need(all(str(review['flag_decisions'][f]).strip() for f in flags),'检测提示的判断依据不能为空')
 return review

def render_binding(job):
 b=read(Path(job)/'build.json');cand=project_path(job,b['candidate']);need(cand.is_file() and sha(cand)==b['sha256'],'候选PPT已变化')
 rp=Path(job)/'render.json';need(rp.is_file(),'没有实际逐页渲染记录')
 r=read(rp);need(r.get('pptx_sha256')==b['sha256'] and r.get('status')=='passed','渲染记录不匹配最终PPT或未通过')
 need(len(r.get('pages',[]))==b['slide_count'],'渲染页数不完整')
 need([im.get('slide') for im in r['pages']]==list(range(1,b['slide_count']+1)),'渲染记录必须按真实页序完整覆盖，不能重复或遗漏页码')
 resolved=[str(project_path(job,im['file'])) for im in r['pages']]
 need(len(set(resolved))==b['slide_count'],'渲染记录不能用同一图片路径代替不同页面')
 for im,fp in zip(r['pages'],resolved):p=Path(fp);need(p.is_file() and sha(p)==im['sha256'],'渲染图片变化或缺失')
 return {'pptx_sha256':b['sha256'],'render_sha256':digest(r)}
