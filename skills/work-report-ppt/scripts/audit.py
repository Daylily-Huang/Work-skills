"""Structural audit only: editability inventory, relationships and page bounds."""
from pathlib import Path
import argparse,hashlib,json,posixpath,zipfile,xml.etree.ElementTree as E
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
def audit(path,expected_font=None,disclosure=None):
    errors=[];slides=[];font_contract=[];disclosure_pages=[]
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist());pres=E.fromstring(z.read('ppt/presentation.xml'));size=pres.find('p:sldSz',NS)
        w,h=int(size.get('cx')),int(size.get('cy'))
        parts=sorted(n for n in names if n.startswith('ppt/slides/slide') and n.endswith('.xml'))
        for name in parts:
            root=E.fromstring(z.read(name));tree=root.find('p:cSld/p:spTree',NS)
            if disclosure and disclosure in ''.join(node.text or '' for node in root.findall('.//a:t',NS)):disclosure_pages.append(name)
            if expected_font:
                allowed={item.strip() for item in expected_font.split(',')}
                for props in root.findall('.//a:rPr',NS)+root.findall('.//a:defRPr',NS):
                    latin=props.find('a:latin',NS)
                    if latin is None or latin.get('typeface','').startswith('+'):continue
                    ea=props.find('a:ea',NS)
                    if ea is None or ea.get('typeface') not in allowed:
                        font_contract.append({'slide':name,'latin':latin.get('typeface'),'east_asian':None if ea is None else ea.get('typeface')})
                        break
            for shape in tree:
                x=shape.find('p:spPr/a:xfrm',NS)
                if x is None:x=shape.find('p:grpSpPr/a:xfrm',NS)
                if x is None:continue
                off,ext=x.find('a:off',NS),x.find('a:ext',NS)
                if off is None or ext is None:continue
                a,b,c,d=[int(node.get(key)) for node,key in [(off,'x'),(off,'y'),(ext,'cx'),(ext,'cy')]]
                if a<-9525 or b<-9525 or a+c>w+9525 or b+d>h+9525:errors.append({'slide':name,'issue':'outside_page'})
            slides.append({'part':name,'native_text_boxes':len(root.findall('.//p:sp[p:txBody]',NS)),
                           'native_shapes':len(root.findall('.//p:sp',NS)),'pictures':len(root.findall('.//p:pic',NS)),
                           'charts':sum(1 for v in root.iter() if v.tag.endswith('}chart'))})
        for name in [n for n in names if n.endswith('.rels')]:
            owner=name.replace('/_rels/','/').removesuffix('.rels') if name!='_rels/.rels' else ''
            for rel in E.fromstring(z.read(name)):
                if rel.get('TargetMode')=='External':continue
                target=rel.get('Target','');resolved=posixpath.normpath(posixpath.join(posixpath.dirname(owner),target)).lstrip('/')
                if resolved not in names:errors.append({'relationship':name,'missing':resolved})
    return {'file':str(Path(path).resolve()),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'structural_ok':not errors,'errors':errors,'slides':slides,
            'font_contract':font_contract,'font_contract_ok':not font_contract,
            'disclosure_pages':len(disclosure_pages) if disclosure else None,
            'disclosure_complete':(len(disclosure_pages)==len(slides)) if disclosure else None,
            'visual_validation':'not_performed','semantic_validation':'not_performed'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('file');ap.add_argument('--report');ap.add_argument('--expected-font');ap.add_argument('--disclosure');a=ap.parse_args();result=audit(a.file,a.expected_font,a.disclosure)
    if a.report:
        p=Path(a.report)
        if p.exists():ap.error('Report exists')
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(not (result['structural_ok'] and result['font_contract_ok'] and result['disclosure_complete'] is not False))
