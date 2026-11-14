"""Compose native PPTX pages by copying their complete OPC dependency graphs."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
from io import BytesIO
from xml.etree import ElementTree as E
from functools import lru_cache
import posixpath,re,hashlib
from common import ROOT,NS,tag,sha,need,read

for prefix,uri in NS.items():E.register_namespace(prefix,uri)
def xml(b):return E.fromstring(b)
def dump(e):return E.tostring(e,encoding='utf-8',xml_declaration=True)
def relpath(p):
 folder,name=posixpath.split(p);return posixpath.join(folder,'_rels',name+'.rels')
def resolve(owner,target):return target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner),target))
def text_of(shape):return '\n'.join(''.join(t.text or '' for t in p.findall('.//a:t',NS)) for p in shape.findall('a:p',NS))
def fields(root):
 out=[]
 for shape in root.findall('.//p:sp',NS):
  body=shape.find('p:txBody',NS);prop=shape.find('p:nvSpPr/p:cNvPr',NS)
  if body is None or prop is None:continue
  name=prop.get('name','');field=name[5:] if name.startswith('slot.') else 'shape.'+prop.get('id','')
  if body.findall('a:p',NS):out.append((field,shape,body))
 return out
@lru_cache(maxsize=48)
def package(path,hash_):
 with ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def slide_parts(parts):
 p=xml(parts['ppt/presentation.xml']);r=xml(parts['ppt/_rels/presentation.xml.rels']);rels={x.get('Id'):resolve('ppt/presentation.xml',x.get('Target')) for x in r}
 return [rels[x.get(tag('r','id'))] for x in p.findall('p:sldIdLst/p:sldId',NS)]
def excel_col(idx):
 s=''
 while idx>=0:s=chr(65+(idx%26))+s;idx=idx//26-1
 return s
def is_num(v):return isinstance(v,(int,float)) and not isinstance(v,bool)
def canonical_part(part):return re.sub(r'^(?:ppt/teacher/[^/]+/(?:shared|page\d+)/)+','',part)
def inventory(path,page):
 path=Path(path).resolve();hash_=sha(path);parts=package(str(path),hash_);order=slide_parts(parts)
 need(isinstance(page,int) and 1<=page<=len(order),'模板页码超出范围')
 part=order[page-1];root=xml(parts[part]);t=[]
 for key,shape,body in fields(root):
  ext=shape.find('p:spPr/a:xfrm/a:ext',NS);sz_val=0
  for sel in ('.//a:rPr','.//a:defRPr','.//a:endParaRPr'):
   node=next((n for n in body.findall(sel,NS) if n.get('sz')),None)
   if node is not None:sz_val=int(node.get('sz'));break
  font_pt=round(sz_val/100,2) if sz_val else None
  w_pt=round(int(ext.get('cx','0'))/12700,1) if ext is not None and ext.get('cx') else None
  h_pt=round(int(ext.get('cy','0'))/12700,1) if ext is not None and ext.get('cy') else None
  eff_sz=font_pt if font_pt and font_pt>0 else 18.0
  t.append({'field':key,'text':text_of(body),'font_size_pt':font_pt,'width_pt':w_pt,'height_pt':h_pt,'max_chars_per_line':max(1,int(w_pt//eff_sz)) if w_pt else None,'max_lines':max(1,int((h_pt+3)//(eff_sz*1.25))) if h_pt else None})
 need(len({x['field'] for x in t})==len(t),'当前页文字字段id重名，先修复或采用原生Office窄改')
 tables=[]
 for table in root.findall('.//a:tbl',NS):
  rows=table.findall('a:tr',NS);tables.append({'rows':len(rows),'columns':len(rows[0].findall('a:tc',NS)),'values':[[text_of(c.find('a:txBody',NS)) for c in row.findall('a:tc',NS)] for row in rows]})
 charts=[];relationships=xml(parts[relpath(part)]);rs={r.get('Id'):resolve(part,r.get('Target')) for r in relationships}
 for c in root.findall('.//c:chart',NS):
  cp=rs[c.get(tag('r','id'))];cr=xml(parts[cp]);charts.append({'part':cp,'series_count':len(cr.findall('.//c:ser',NS))})
 note_part=next((resolve(part,r.get('Target')) for r in relationships if r.get('Type','').endswith('/notesSlide')),None)
 notes_text=''
 if note_part and note_part in parts:
  nr=xml(parts[note_part]);nb=[]
  for sh in nr.findall('.//p:sp',NS):
   ph=sh.find('p:nvSpPr/p:nvPr/p:ph',NS)
   if ph is not None and ph.get('type')=='body':
    txt=text_of(sh.find('p:txBody',NS)).strip()
    if txt:nb.append(txt)
  notes_text='\n'.join(nb)
 return {'path':str(path),'sha256':hash_,'page':page,'part':part,'text_fields':t,'tables':tables,'charts':charts,'notes_text':notes_text}

def set_body(body,value):
 text=str(value).replace('\r\n','\n').replace('\r','\n')
 if text==text_of(body):return
 paras=body.findall('a:p',NS)
 if '\n' not in text and len(paras)==1:
  runs=paras[0].findall('a:r',NS)
  styles=[r.find('a:rPr',NS) for r in runs]
  if len(runs)>1 and len({E.tostring(s) if s is not None else b'' for s in styles})>1:
   lens=[len(''.join(t.text or '' for t in r.findall('a:t',NS))) for r in runs];total=sum(lens)
   if total>0:
    p=paras[0];pr=p.find('a:pPr',NS);end=p.find('a:endParaRPr',NS)
    pr_copy=deepcopy(pr) if pr is not None else None;end_copy=deepcopy(end) if end is not None else None
    style_copies=[deepcopy(s) if s is not None else None for s in styles]
    p.clear()
    if pr_copy is not None:p.append(pr_copy)
    pos=0;acc=0;n=len(text)
    for idx,(ln,st) in enumerate(zip(lens,style_copies)):
     acc+=ln
     end_pos=n if idx==len(lens)-1 else round(n*acc/total)
     chunk=text[pos:end_pos];pos=end_pos
     if chunk or (n==0 and idx==0):
      run=E.SubElement(p,tag('a','r'))
      if st is not None:run.append(st)
      E.SubElement(run,tag('a','t')).text=chunk
    if end_copy is not None:p.append(end_copy)
    return
 prototype=body.find('a:p',NS)
 if prototype is None:prototype=E.Element(tag('a','p'))
 oldrun=prototype.find('a:r',NS);style=deepcopy(oldrun.find('a:rPr',NS)) if oldrun is not None and oldrun.find('a:rPr',NS) is not None else None
 for p in list(body):
  if p.tag==tag('a','p'):body.remove(p)
 for line in text.split('\n'):
  p=E.SubElement(body,tag('a','p'));pr=prototype.find('a:pPr',NS)
  if pr is not None:p.append(deepcopy(pr))
  run=E.SubElement(p,tag('a','r'))
  if style is not None:run.append(deepcopy(style))
  E.SubElement(run,tag('a','t')).text=line
  end=prototype.find('a:endParaRPr',NS)
  if end is not None:p.append(deepcopy(end))

def workbook(categories,series):
 x='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
 sheet=E.Element('{'+x+'}worksheet');data=E.SubElement(sheet,'{'+x+'}sheetData')
 vals=[['类别']+[s['name'] for s in series]]+[[c]+[s['values'][i] for s in series] for i,c in enumerate(categories)]
 for ri,row in enumerate(vals,1):
  r=E.SubElement(data,'{'+x+'}row',r=str(ri))
  for ci,v in enumerate(row):
   c=E.SubElement(r,'{'+x+'}c',r=f'{excel_col(ci)}{ri}')
   if is_num(v):E.SubElement(c,'{'+x+'}v').text=str(v)
   else:c.set('t','inlineStr');E.SubElement(E.SubElement(c,'{'+x+'}is'),'{'+x+'}t').text=str(v)
 wb=E.Element('{'+x+'}workbook');sheets=E.SubElement(wb,'{'+x+'}sheets');E.SubElement(sheets,'{'+x+'}sheet',name='Sheet1',sheetId='1',attrib={tag('r','id'):'rId1'})
 rel=f'<Relationships xmlns="{NS["rel"]}"><Relationship Id="rId1" Type="{NS["r"]}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
 ct=f'<Types xmlns="{NS["ct"]}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'
 out=BytesIO()
 with ZipFile(out,'w',ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml',ct);z.writestr('_rels/.rels',f'<Relationships xmlns="{NS["rel"]}"><Relationship Id="rId1" Type="{NS["r"]}/officeDocument" Target="xl/workbook.xml"/></Relationships>');z.writestr('xl/workbook.xml',dump(wb));z.writestr('xl/_rels/workbook.xml.rels',rel);z.writestr('xl/worksheets/sheet1.xml',dump(sheet))
 return out.getvalue()
def chart_cache(parent,name,formula,values,numeric=False):
 node=parent.find('c:'+name,NS)
 if node is None:node=E.SubElement(parent,tag('c',name))
 node.clear();ref=E.SubElement(node,tag('c','numRef' if numeric else 'strRef'));E.SubElement(ref,tag('c','f')).text=formula
 cache=E.SubElement(ref,tag('c','numCache' if numeric else 'strCache'))
 if numeric:E.SubElement(cache,tag('c','formatCode')).text='General'
 E.SubElement(cache,tag('c','ptCount'),val=str(len(values)))
 for i,value in enumerate(values):E.SubElement(E.SubElement(cache,tag('c','pt'),idx=str(i)),tag('c','v')).text=str(value)
def change_chart(parts,cp,data):
 root=xml(parts[cp]);categories=data['categories'];series=data['series'];n=len(categories)
 for i,(ser,values) in enumerate(zip(root.findall('.//c:ser',NS),series)):
  col=excel_col(1+i);chart_cache(ser,'tx',f'Sheet1!${col}$1',[values['name']]);chart_cache(ser,'cat',f'Sheet1!$A$2:$A${n+1}',categories);chart_cache(ser,'val',f'Sheet1!${col}$2:${col}${n+1}',values['values'],True)
  for point in list(ser.findall('c:dPt',NS)):
   idx=point.find('c:idx',NS)
   if idx is not None and int(idx.get('val'))>=n:ser.remove(point)
 ext=root.find('c:externalData',NS);need(ext is not None,'源图表缺少嵌入数据工作簿，不能只改缓存')
 rels=xml(parts[relpath(cp)]);target=next(r.get('Target') for r in rels if r.get('Id')==ext.get(tag('r','id')))
 parts[resolve(cp,target)]=workbook(categories,series);parts[cp]=dump(root)

def patch_page(parts,inv,page,brief):
 parts=dict(parts);part=inv['part'];root=xml(parts[part])
 for key,shape,body in fields(root):
  if key in page['text']:set_body(body,page['text'][key])
 for table,values in zip(root.findall('.//a:tbl',NS),page.get('tables',[])):
  for row,vals in zip(table.findall('a:tr',NS),values['values']):
   for cell,v in zip(row.findall('a:tc',NS),vals):set_body(cell.find('a:txBody',NS),v)
 parts[part]=dump(root)
 for c,values in zip(inv['charts'],page.get('charts',[])):change_chart(parts,c['part'],values)
 rels=xml(parts[relpath(part)]);note=next((resolve(part,r.get('Target')) for r in rels if r.get('Type','').endswith('/notesSlide')),None)
 ss={s['id']:s for s in brief.get('sources',[])}
 used=set(page.get('source_ids',[]))
 for key in page.get('fact_ids',[]):
  fact=next((f for f in page.get('_facts',[]) if f['id']==key),None)
  if fact:used.update(fact.get('source_ids',[]))
 preserve_existing=bool(page.get('source_deck')) and ('teacher_notes' not in page or page.get('keep_notes'))
 if preserve_existing and not page.get('teacher_guidance') and not used:
  return parts
 notes=inv.get('notes_text','') if preserve_existing else (page.get('teacher_notes') or '')
 if page.get('teacher_guidance') and brief.get('constraints',{}).get('answers')!='omit':
  guidance='教学提示：'+page['teacher_guidance']
  if guidance not in notes:notes=(notes+'\n'+guidance).strip() if notes.strip() else guidance
 if used:
  src_line='来源：'+'；'.join(ss[x].get('title',x)+' '+ss[x].get('location','') for x in sorted(used))
  if src_line not in notes:notes=(notes+'\n'+src_line).strip() if notes.strip() else src_line
 if note:
  nr=xml(parts[note]);bodies=[]
  for sh in nr.findall('.//p:sp',NS):
   ph=sh.find('p:nvSpPr/p:nvPr/p:ph',NS)
   if ph is not None and ph.get('type')=='body':bodies.append(sh.find('p:txBody',NS))
  if bodies:
   set_body(bodies[0],notes.strip())
   for b in bodies[1:]:set_body(b,'')
   parts[note]=dump(nr)
  else:need(not notes.strip(),'源文件没有可用备注区，不能悄悄丢失教师提示')
 else:need(not notes.strip(),'源页没有备注页，请采用有备注的随包版式或使用原生Office补充备注')
 return parts

class Composer:
 def __init__(self):self.parts={};self.shared={};self.types={};self.defaults={'rels':'application/vnd.openxmlformats-package.relationships+xml','xml':'application/xml'};self.slide_order=[];self.masters=[];self.notes_masters=[]
 def import_page(self,path,hash_,inv,page,brief,index):
  raw=package(str(path),hash_);working=patch_page(raw,inv,page,brief);scope={};sourcekey=hash_[:12];ct=xml(raw['[Content_Types].xml']);types={n.get('PartName').lstrip('/'):n.get('ContentType') for n in ct if n.tag==tag('ct','Override')};source_defaults={n.get('Extension'):n.get('ContentType') for n in ct if n.tag==tag('ct','Default')}
  for n in ct:
   if n.tag==tag('ct','Default'):
    ext=n.get('Extension');ctype=n.get('ContentType');self.defaults.setdefault(ext,ctype)
  def copy(part):
   canon=canonical_part(part)
   globalpart=canon.startswith(('ppt/media/','ppt/slideMasters/','ppt/slideLayouts/','ppt/notesMasters/','ppt/theme/'))
   m=re.match(r'^(?:ppt/teacher/[^/]+/(?:shared|page\d+)/)*(ppt/teacher/([^/]+)/(?:shared|page\d+)/(.+))$',part)
   if m:
    orig_hash=m.group(2);inner=m.group(3)
    cache=self.shared if globalpart else scope;key=(sourcekey,orig_hash,inner) if globalpart else inner
    dest_rel=f'{orig_hash}/{inner}' if globalpart else inner
   else:
    cache=self.shared if globalpart else scope;key=(sourcekey,canon) if globalpart else canon
    dest_rel=canon
   if key in cache:return cache[key]
   need(part in working,f'PPT关系指向缺失部件：{part}')
   target=f'ppt/teacher/{sourcekey}/'+('shared/' if globalpart else f'page{index:03d}/')+dest_rel;cache[key]=target
   self.parts[target]=working[part]
   ctype=types.get(part,source_defaults.get(Path(part).suffix.lstrip('.')))
   if ctype:self.types[target]=ctype
   if types.get(part,'').endswith('presentationml.slideMaster+xml') and target not in self.masters:self.masters.append(target)
   if types.get(part,'').endswith('presentationml.notesMaster+xml') and target not in self.notes_masters:self.notes_masters.append(target)
   rp=relpath(part)
   if rp in working:
    rr=xml(working[rp])
    for rel in rr:
     if rel.get('TargetMode')=='External':continue
     dependency=resolve(part,rel.get('Target'));mapped=copy(dependency);rel.set('Target',posixpath.relpath(mapped,posixpath.dirname(target)))
    self.parts[relpath(target)]=dump(rr)
   return target
  self.slide_order.append(copy(inv['part']))
 def save(self,path,base):
  if self.notes_masters:
   for name in list(self.parts):
    if not name.endswith('.rels'):continue
    rr=xml(self.parts[name]);changed=False;owner=name.replace('/_rels/','/')[:-5]
    for link in rr:
     if link.get('Type','').endswith('/notesMaster'):
      link.set('Target',posixpath.relpath(self.notes_masters[0],posixpath.dirname(owner)));changed=True
    if changed:self.parts[name]=dump(rr)
  layout_index=0
  for master in self.masters:
   node=xml(self.parts[master])
   for layout in node.findall('p:sldLayoutIdLst/p:sldLayoutId',NS):
    layout.set('id',str(2147484000+layout_index));layout_index+=1
   self.parts[master]=dump(node)
  p=E.Element(tag('p','presentation'));r=E.Element(tag('rel','Relationships'));ml=E.SubElement(p,tag('p','sldMasterIdLst'))
  for i,master in enumerate(self.masters):
   rid='master'+str(i);E.SubElement(ml,tag('p','sldMasterId'),id=str(2147483648+i),attrib={tag('r','id'):rid});E.SubElement(r,tag('rel','Relationship'),Id=rid,Type=NS['r']+'/slideMaster',Target=posixpath.relpath(master,'ppt'))
  if self.notes_masters:
   # Use one notes master consistently for imported teacher notes.
   nl=E.SubElement(p,tag('p','notesMasterIdLst'));E.SubElement(nl,tag('p','notesMasterId'),attrib={tag('r','id'):'notesMaster'});E.SubElement(r,tag('rel','Relationship'),Id='notesMaster',Type=NS['r']+'/notesMaster',Target=posixpath.relpath(self.notes_masters[0],'ppt'))
  sl=E.SubElement(p,tag('p','sldIdLst'))
  for i,part in enumerate(self.slide_order):
   rid='slide'+str(i);E.SubElement(sl,tag('p','sldId'),id=str(256+i),attrib={tag('r','id'):rid});E.SubElement(r,tag('rel','Relationship'),Id=rid,Type=NS['r']+'/slide',Target=posixpath.relpath(part,'ppt'))
  original=xml(base['ppt/presentation.xml'])
  for name in ['sldSz','notesSz','defaultTextStyle']:
   el=original.find('p:'+name,NS)
   if el is not None:p.append(deepcopy(el))
  self.parts['ppt/presentation.xml']=dump(p);self.types['ppt/presentation.xml']='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml';self.parts['ppt/_rels/presentation.xml.rels']=dump(r)
  self.parts['_rels/.rels']=(f'<Relationships xmlns="{NS["rel"]}"><Relationship Id="rId1" Type="{NS["r"]}/officeDocument" Target="ppt/presentation.xml"/></Relationships>').encode()
  reachable={'_rels/.rels','[Content_Types].xml'};queue=['_rels/.rels']
  while queue:
   curr=queue.pop()
   if curr.endswith('.rels') and curr in self.parts:
    owner='root.xml' if curr=='_rels/.rels' else curr.replace('/_rels/','/')[:-5]
    for link in xml(self.parts[curr]):
     if link.get('TargetMode')=='External':continue
     target=resolve(owner,link.get('Target'))
     if target not in reachable:reachable.add(target);queue.append(target)
     rp=relpath(target)
     if rp in self.parts and rp not in reachable:reachable.add(rp);queue.append(rp)
  for k in list(self.parts):
   if k not in reachable:del self.parts[k];self.types.pop(k,None)
  ct=E.Element(tag('ct','Types'))
  for ext,ctype in self.defaults.items():E.SubElement(ct,tag('ct','Default'),Extension=ext,ContentType=ctype)
  for name,ctype in self.types.items():E.SubElement(ct,tag('ct','Override'),PartName='/'+name,ContentType=ctype)
  self.parts['[Content_Types].xml']=dump(ct)
  with ZipFile(path,'w',ZIP_DEFLATED) as z:
   for name,data in self.parts.items():z.writestr(name,data)

def audit(path):
 with ZipFile(path) as z:
  parts={n:z.read(n) for n in z.namelist()};need(z.testzip() is None,'PPTX ZIP损坏')
  order=slide_parts(parts);counts=[]
  for rel,data in parts.items():
   if rel.endswith('.rels'):
    owner=rel.replace('/_rels/','/')[:-5]
    if rel=='_rels/.rels':owner='root.xml'
    for r in xml(data):
     if r.get('TargetMode')!='External':need(resolve(owner,r.get('Target')) in parts,f'失效PPT部件关系：{rel} {r.get("Target")}')
  reachable={'_rels/.rels','[Content_Types].xml'};queue=['_rels/.rels']
  while queue:
   curr=queue.pop()
   if curr.endswith('.rels') and curr in parts:
    owner='root.xml' if curr=='_rels/.rels' else curr.replace('/_rels/','/')[:-5]
    for r in xml(parts[curr]):
     if r.get('TargetMode')!='External':
      target=resolve(owner,r.get('Target'))
      if target not in reachable:reachable.add(target);queue.append(target)
      rp=relpath(target)
      if rp in parts and rp not in reachable:reachable.add(rp);queue.append(rp)
  orphans=sorted(set(parts)-reachable)
  need(not orphans,f'存在未引用的孤儿PPT部件：{orphans}')
  for part in order:
   root=xml(parts[part]);counts.append({'text':len(fields(root)),'tables':len(root.findall('.//a:tbl',NS)),'charts':len(root.findall('.//c:chart',NS)),'pictures':len(root.findall('.//p:pic',NS))})
  return {'status':'passed','sha256':sha(path),'slide_count':len(order),'pages':counts}
