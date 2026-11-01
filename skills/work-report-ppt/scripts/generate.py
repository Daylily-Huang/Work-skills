"""Create native editable decks from an explicit content plan (Python + python-pptx).

No network, hidden image generation, fabricated business data or external tool names.
All decks require clarified requirements and individual page plans. Drafts cannot bypass ambiguity.
"""
from pathlib import Path
import argparse,hashlib,json,math,os,sys,tempfile
from pptx import Presentation
from pptx.util import Inches,Pt,Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE,XL_LEGEND_POSITION
from PIL import Image
from design_gate import validate as design_errors
from design_gate import requirements_errors
from plan_gate import validate as plan_errors
from approval_gate import validate as approval_errors
from text_style import set_cjk_font
from chrome import header,data_table
from report_logic import prepare as prepare_report

ROOT=Path(__file__).resolve().parents[1]
W,H=1280,720
# Typographic rhythm for body copy. Chinese needs far more air than the Latin default:
# 1.62x the glyph size per line, 0.46x between paragraphs. The overflow check below
# uses these same constants, so a box that passes here also fits in PowerPoint.
BODY_LEADING=1.62
PARA_GAP=0.46
BOX_TOLERANCE=6

def _char_width(char,size):
    """Advance width in CSS pixels. A CJK glyph is one em; Latin averages about half."""
    return size*(1.0 if ord(char)>0x2E80 else 0.56)

def _wrapped_lines(value,w,size):
    """Count rendered lines the way PowerPoint does: break per glyph once the line is full."""
    total=0
    for paragraph in str(value).split('\n'):
        used=0;count=1
        for char in paragraph:
            width=_char_width(char,size)
            if used+width>w and used>0:
                count+=1;used=width
            else:
                used+=width
        total+=count
    return total
def unit(px):return Inches(px/96)
def rgb(value):return RGBColor.from_string(value.lstrip('#'))
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

class Canvas:
    def __init__(self,slide,palette,font='Microsoft YaHei',style='editorial',display=None):
        self.s=slide;self.p=palette;self.font=font;self.style=style
        # Display face carries headlines and large numerals only; body copy stays on the sans face.
        self.display=display or font
        slide.background.fill.solid();slide.background.fill.fore_color.rgb=rgb(palette['paper'])
    def shape(self,x,y,w,h,fill=None,line=None,kind=MSO_SHAPE.RECTANGLE):
        sh=self.s.shapes.add_shape(kind,unit(x),unit(y),unit(w),unit(h))
        if fill:sh.fill.solid();sh.fill.fore_color.rgb=rgb(fill)
        else:sh.fill.background()
        if line:sh.line.color.rgb=rgb(line);sh.line.width=Pt(.8)
        else:sh.line.fill.background()
        for effect in sh._element.xpath('./p:style/a:effectRef'):effect.set('idx','0')
        return sh
    def line(self,x,y,x2,y2,color=None,width=1):
        sh=self.s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,unit(x),unit(y),unit(x2),unit(y2))
        sh.line.color.rgb=rgb(color or self.p['secondary']);sh.line.width=Pt(width)
        for effect in sh._element.xpath('./p:style/a:effectRef'):effect.set('idx','0')
        return sh
    def text(self,value,x,y,w,h,size=24,color=None,bold=False,align=PP_ALIGN.LEFT,display=False,leading=None,gap=None):
        value=str(value)
        if size<11:raise ValueError(f'Projection minimum is 11pt; split the content instead of shrinking: {value[:40]}')
        # Layout dimensions and historical size inputs are CSS pixels (96dpi).
        # 14px is 10.5pt: enforce the actual PowerPoint font floor in points.
        size=max(size,11/.75)
        lead=BODY_LEADING if leading is None else leading
        pgap=PARA_GAP if gap is None else gap
        # Reject excessive copy instead of silently shrinking or truncating text.
        lines=_wrapped_lines(value,w,size)
        need=lines*size*lead+max(0,lines-1)*size*pgap
        if need>h+BOX_TOLERANCE:
            # PPT_TEXT_REPORT lists every tight box at once instead of failing on the first page.
            if os.environ.get('PPT_TEXT_REPORT'):
                print(f'OVER need={need:.0f} box={h} size={size} y={y} {value[:34]!r}')
            else:
                raise ValueError(f'Text needs {need:.0f}px but its box holds {h}: {value[:55]}')
        face=self.display if display else self.font
        sh=self.s.shapes.add_textbox(unit(x),unit(y),unit(w),unit(h));tf=sh.text_frame
        tf.clear();tf.word_wrap=True;tf.margin_left=tf.margin_right=0;tf.margin_top=tf.margin_bottom=0
        for i,line in enumerate(value.split('\n')):
            p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.alignment=align
            set_cjk_font(p.font,face);p.font.size=Pt(size*.75)
            p.line_spacing=Pt(size*.75*lead);p.space_after=Pt(size*.75*pgap)
            p.font.bold=bold;p.font.color.rgb=rgb(color or self.p.get('ink','#20272C'))
            for run in p.runs:set_cjk_font(run.font,face)
        return sh
    def item(self,item,x,y,w,h,number=None):
        title=item.get('title','');body=item.get('body','')
        if number is not None:self.text(f'{number:02}',x,y,48,42,28,self.p['accent'],True);x+=62;w-=62
        self.text(title,x,y,w,50,26,self.p['primary'],True)
        if body:self.text(body,x,y+62,w,h-62,23)
    def picture(self,path,x,y,w,h,caption=''):
        p=Path(path)
        if not p.is_file():raise FileNotFoundError(p)
        with Image.open(p) as im:iw,ih=im.size
        scale=min(w/iw,h/ih);tw,th=iw*scale,ih*scale
        self.s.shapes.add_picture(str(p),unit(x+(w-tw)/2),unit(y+(h-th)/2),unit(tw),unit(th))
        if caption:self.text(caption,x,y+h+12,w,36,16,self.p['secondary'])

def add_document_disclosure(prs,palette,font,label):
    """Write the disclosure on every slide, independent of the chosen layout."""
    if not label:return 0
    placed=0
    for slide in prs.slides:
        box=slide.shapes.add_textbox(unit(33),unit(689),unit(1100),unit(23));tf=box.text_frame
        tf.clear();tf.word_wrap=True;tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
        p=tf.paragraphs[0];p.text=label
        set_cjk_font(p.font,font);p.font.size=Pt(12);p.font.color.rgb=rgb(palette['secondary'])
        for run in p.runs:set_cjk_font(run.font,font)
        placed+=1
    return placed

def items_for(s,min_items=1,max_items=6):
    items=s.get('items',[])
    if not isinstance(items,list) or not min_items<=len(items)<=max_items:raise ValueError(f"{s['layout']} requires {min_items}–{max_items} items")
    if not all(isinstance(i,dict) and isinstance(i.get('title'),str) for i in items):raise ValueError('Items need title and optional body strings')
    return items

def chart(c,s,kind):
    d=s.get('chart',{});cats=d.get('categories',[]);series=d.get('series',[])
    if not 1<=len(cats)<=10 or not 1<=len(series)<=3:raise ValueError('Chart needs 1–10 categories and 1–3 series')
    data=CategoryChartData();data.categories=cats
    for row in series:
        if len(row.get('values',[]))!=len(cats) or not all(finite(v) for v in row['values']):raise ValueError('Chart values must match categories and be finite')
        data.add_series(row['name'],row['values'])
    ch=c.s.shapes.add_chart(kind,unit(48),unit(205),unit(860),unit(400),data).chart
    # The page already supplies the title. Office otherwise inserts a default
    # chart title with theme fonts, bypassing the explicit CJK text contract.
    ch.has_title=False
    ch.has_legend=len(series)>1
    if ch.has_legend:ch.legend.position=XL_LEGEND_POSITION.BOTTOM;ch.legend.font.size=Pt(12);set_cjk_font(ch.legend.font,c.font)
    ch.category_axis.tick_labels.font.size=Pt(12);ch.value_axis.tick_labels.font.size=Pt(12)
    set_cjk_font(ch.category_axis.tick_labels.font,c.font);set_cjk_font(ch.value_axis.tick_labels.font,c.font)
    for i,sr in enumerate(ch.series):
        color=[c.p['primary'],c.p['accent'],c.p['secondary']][i]
        if kind==XL_CHART_TYPE.LINE:
            sr.format.line.color.rgb=rgb(color);sr.format.line.width=Pt(2.5)
        else:
            sr.invert_if_negative=False
            sr.format.fill.solid();sr.format.fill.fore_color.rgb=rgb(color)
    c.text(s.get('insight',''),954,235,275,260,27,c.p['primary'],True)
    c.text(s.get('unit',''),48,619,900,28,15,c.p['secondary'])

def render_layout(c,s,idx,tag,draft,base):
    kind=s['layout'];p=c.p
    if kind.startswith('office_'):
        from commercial_layouts import render
        render(c,s,idx,tag,draft,base)
        return
    if kind=='cover':
        # One cover composition: statement on the left, working nodes on a tinted panel at right.
        from commercial_layouts import panel as _panel,ribbon as _ribbon
        items=[i for i in s.get('items',[]) if isinstance(i,dict)][:4]
        dark=c.style.startswith('black') or c.style.startswith('red')
        c.shape(40,60,5,36,p['accent'])
        c.text(tag,58,62,700,28,15,p['secondary'])
        c.text(s['title'],58,144,700,196,52,p['ink'] if dark else p['primary'],True,display=True)
        if s.get('subtitle'):c.text(s['subtitle'],60,352,690,84,23,p['secondary'])
        c.line(60,458,196,458,p['accent'],4)
        if s.get('meta'):c.text(s['meta'],60,486,700,62,17,p['secondary'])
        if items:
            _panel(c,752,116,496,486)
            _ribbon(c,'关键工作节点',772,136,320)
            for i,it in enumerate(items):
                y=206+i*94
                c.shape(792,y+7,22,22,p['primary'],kind=MSO_SHAPE.OVAL)
                if i<len(items)-1:c.line(803,y+29,803,y+101,p['secondary'],1.6)
                c.text(it.get('title',''),838,y,380,32,21,p['ink'],True)
                if it.get('body'):c.text(it['body'],838,y+36,380,42,16,p['secondary'])
        if draft:c.text('合成演示 · 设计草稿',48,688,1100,22,12,p['secondary'])
        return
    header(c,s['title'],tag,idx,draft)
    if kind=='statement':
        # Conclusion on the left, its evidence in a tinted panel on the right: no page of loose copy.
        from commercial_layouts import panel as _panel
        body=s.get('body','');headline=s.get('headline','')
        # Panel height follows whichever side is taller; a fixed box leaves half the page bare once limits move to notes.
        t_lines=_wrapped_lines(headline,700,46)
        t_need=t_lines*46*BODY_LEADING+max(0,t_lines-1)*46*PARA_GAP
        if body:
            b_lines=_wrapped_lines(body,408,20)
            b_need=b_lines*20*BODY_LEADING+max(0,b_lines-1)*20*PARA_GAP
        else:
            b_need=0
        block=min(max(t_need+44,b_need+86,200),340)
        top=390-block/2
        c.shape(40,top,7,block,p['accent'])
        c.text(headline,76,top+6,700,block-14,46,p['ink'],True,display=True)
        if body:
            _panel(c,780,top,460,block)
            c.text('依据',806,top+26,408,26,15,p['secondary'])
            # Centre the evidence in the panel: the title usually wraps one line short of the estimate.
            body_top=top+max(62,(block-b_need)/2)
            c.text(body,806,body_top,408,max(60,block-(body_top-top)-16),20)
    elif kind in ['contents','agenda']:
        rows=items_for(s,2,5)
        for i,row in enumerate(rows):
            y=200+i*83;c.text(f'{i+1:02}',50,y,60,48,32,p['accent'])
            c.text(row['title'],145,y,550,46,29,p['primary'],True)
            c.text(row.get('body',''),765,y+5,450,44,21,p['secondary']);c.line(145,y+62,1230,y+62,p['tint'])
    elif kind=='section':
        c.text(s.get('number','01'),48,219,400,195,150,p['tint'],True)
        c.text(s.get('headline',s['title']),430,270,760,130,52,p['primary'],True)
        c.text(s.get('body',''),435,445,730,110,25)
    elif kind=='image':
        if s.get('image'):c.picture(base/s['image'],48,202,790,392,s.get('caption',''))
        elif draft:
            c.shape(48,202,790,392,p['tint']);c.text('原图位置\n合成模板不放入虚构证据图',93,337,700,100,28,p['secondary'],align=PP_ALIGN.CENTER)
        else:raise ValueError('Image slide needs a real image file')
        c.text(s.get('headline',''),892,208,338,98,31,p['primary'],True);c.text(s.get('body',''),892,329,338,255,24)
    elif kind=='metrics':
        rows=items_for(s,2,4);n=len(rows);gap=16;cw=(1200-gap*(n-1))/n
        for i,row in enumerate(rows):
            x=40+i*(cw+gap)
            c.shape(x,226,cw,300,p['tint'],kind=MSO_SHAPE.ROUNDED_RECTANGLE)
            # Inset the colour tab so it never clips the rounded corners.
            c.shape(x+16,226,cw-32,4,p['accent'] if i==n-1 else p['primary'])
            c.text(row.get('value','待补'),x+26,262,cw-52,92,56,p['primary'],True,display=True)
            c.text(row['title'],x+26,372,cw-52,50,20,p['ink'],True)
            if row.get('body'):c.text(row['body'],x+26,424,cw-52,88,20,p['secondary'])
    elif kind in ['bar','line']:chart(c,s,XL_CHART_TYPE.COLUMN_CLUSTERED if kind=='bar' else XL_CHART_TYPE.LINE)
    elif kind=='table':
        heads=s.get('columns',[]);rows=s.get('rows',[])
        if not 2<=len(heads)<=6 or not 1<=len(rows)<=7 or any(len(row)!=len(heads) for row in rows):raise ValueError('Table requires 2–6 columns and 1–7 equal-length rows')
        data_table(c,heads,rows,40,248,1200,46+74*len(rows),size=15,head_h=46,note=s.get('note',''))
    elif kind=='comparison':
        for i,row in enumerate(items_for(s,2,2)):
            x=40+i*616
            c.shape(x,196,584,306,p['tint'],kind=MSO_SHAPE.ROUNDED_RECTANGLE)
            c.shape(x+16,196,552,4,p['accent'] if i else p['primary'])
            c.text(row['title'],x+30,226,524,50,24,p['ink'],True,display=True)
            c.line(x+32,290,x+152,290,p['accent'],3)
            c.text(row.get('body',''),x+30,314,524,172,21,p['secondary'])
    elif kind in ['process','timeline','roadmap']:
        rows=items_for(s,2,5);step=1184/len(rows)
        liney=361 if kind=='timeline' else 360
        c.line(80,liney,1190,liney,p['secondary'],2)
        for i,row in enumerate(rows):
            x=48+i*step
            if kind=='timeline':
                c.shape(x,282,step-36,42,p['tint'],kind=MSO_SHAPE.ROUNDED_RECTANGLE)
                c.text(row['title'],x+14,292,step-62,30,22,p['primary'],True,display=True)
                c.shape(x+9,350,22,22,p['accent'],kind=MSO_SHAPE.OVAL)
                c.text(row.get('body',''),x,402,step-32,232,22)
            elif kind=='process':
                c.shape(x,264,step-30,90,p['primary'],kind=MSO_SHAPE.CHEVRON)
                c.text(row['title'],x+18,283,step-72,57,24,'#FFFFFF',True)
                c.text(row.get('body',''),x+6,406,step-42,164,22)
            else:
                c.text(f'{i+1:02}',x,231,step-25,60,43,p['accent'],True)
                c.shape(x,345,step-28,12,p['primary']);c.item(row,x,395,step-35,215)
    elif kind=='swimlane':
        rows=items_for(s,2,4)
        for i,row in enumerate(rows):
            y=208+i*103;c.shape(48,y,1184,88,p['tint'] if i%2==0 else p['paper'])
            c.text(row['title'],65,y+22,220,50,25,p['primary'],True)
            c.line(310,y+12,310,y+77,p['secondary']);c.text(row.get('body',''),345,y+22,850,55,23)
    elif kind in ['funnel','pyramid']:
        rows=items_for(s,3,5)
        for i,row in enumerate(rows):
            width=(770-i*117) if kind=='funnel' else (330+i*117)
            x=48+(820-width)/2;y=209+i*80
            c.shape(x,y,width,65,p['primary'] if i%2==0 else p['secondary'],kind=MSO_SHAPE.TRAPEZOID)
            c.text(row['title'],x+12,y+13,width-24,45,23,'#FFFFFF',True,PP_ALIGN.CENTER)
            c.text(row.get('body',''),900,y+10,320,65,21)
    elif kind in ['matrix','swot']:
        rows=items_for(s,4,4)
        c.line(640,203,640,625,p['secondary']);c.line(48,415,1232,415,p['secondary'])
        for i,row in enumerate(rows):
            x=70+(i%2)*610;y=216+(i//2)*216;c.item(row,x,y,535,180)
    elif kind=='cycle':
        rows=items_for(s,3,4);positions=[(480,195),(900,360),(480,520),(65,360)]
        for i,row in enumerate(rows):
            x,y=positions[i];c.shape(x,y,280,80,p['tint'],p['secondary'],MSO_SHAPE.ROUNDED_RECTANGLE)
            c.text(row['title'],x+16,y+18,248,48,25,p['primary'],True,PP_ALIGN.CENTER)
        c.line(780,276,913,350,p['accent'],2);c.line(908,452,781,515,p['accent'],2)
        if len(rows)==4:c.line(464,521,330,451,p['accent'],2);c.line(329,348,465,274,p['accent'],2)
        else:
            c.line(480,560,385,560,p['accent'],2);c.line(385,560,385,235,p['accent'],2);c.line(385,235,480,235,p['accent'],2)
        c.text(s.get('body',''),450,320,380,178,27,p['primary'],align=PP_ALIGN.CENTER)
    elif kind=='org':
        rows=items_for(s,3,5);c.shape(480,205,320,75,p['primary']);c.text(s.get('root','项目负责人'),500,223,280,45,26,'#FFFFFF',True,PP_ALIGN.CENTER)
        c.line(640,280,640,345,p['secondary'],2);c.line(130,345,1130,345,p['secondary'],2)
        step=1184/len(rows)
        for i,row in enumerate(rows):
            x=48+i*step;c.line(x+step/2,345,x+step/2,390,p['secondary'],2);c.item(row,x+8,410,step-25,187)
    elif kind=='quote':
        c.text('“',48,191,130,175,130,p['accent']);c.text(s.get('quote',''),194,230,1010,235,46,p['primary'])
        c.line(198,521,400,521,p['secondary']);c.text(s.get('attribution',''),198,554,1000,55,23,p['secondary'])
    elif kind=='team':
        rows=items_for(s,2,4);step=1184/len(rows)
        for i,row in enumerate(rows):
            x=48+i*step;c.text(f'{i+1:02}',x,223,step-30,95,75,p['tint'],True);c.item(row,x,354,step-40,238)
    elif kind=='case':
        rows=items_for(s,3,3)
        for i,row in enumerate(rows):c.item(row,48+i*400,238,350,340,i+1)
    elif kind=='architecture':
        rows=items_for(s,3,4)
        for i,row in enumerate(rows):
            y=205+i*103;c.shape(48,y,1184,80,p['tint'],p['secondary']);c.text(row['title'],70,y+21,300,50,27,p['primary'],True)
            c.text(row.get('body',''),405,y+21,795,53,23)
    elif kind=='risks':
        rows=items_for(s,2,4)
        for i,row in enumerate(rows):
            y=194+i*124
            c.shape(40,y,1200,104,p['tint'],kind=MSO_SHAPE.ROUNDED_RECTANGLE)
            c.shape(40,y,6,104,p['accent'])
            c.text(f'{i+1:02}',70,y+28,66,52,32,p['accent'],True,display=True)
            c.text(row['title'],150,y+28,330,54,24,p['ink'],True)
            c.text(row.get('body',''),500,y+31,720,78,21,p['secondary'])
    elif kind=='pricing':
        rows=items_for(s,2,3);step=1184/len(rows)
        for i,row in enumerate(rows):
            x=48+i*step;c.line(x,211,x+step-40,211,p['primary'],4);c.text(row['title'],x,243,step-45,66,32,p['primary'],True)
            c.text(row.get('value','待确认'),x,337,step-45,85,48,p['accent'],True);c.text(row.get('body',''),x,459,step-45,149,23)
    elif kind=='gallery':
        rows=items_for(s,2,4);step=1184/len(rows)
        for i,row in enumerate(rows):
            x=48+i*step
            if row.get('image'):c.picture(base/row['image'],x,205,step-24,294)
            elif draft:c.shape(x,205,step-24,294,p['tint']);c.text('素材位置',x+12,318,step-48,50,25,p['secondary'],align=PP_ALIGN.CENTER)
            else:raise ValueError('Gallery items require actual image files')
            c.text(row['title'],x,533,step-25,70,25,p['primary'],True)
    elif kind=='lesson':
        rows=items_for(s,3,3)
        for i,row in enumerate(rows):
            y=210+i*135;c.text(row['title'],48,y,300,64,30,p['primary'],True);c.line(383,y,383,y+95,p['accent'],2)
            c.text(row.get('body',''),425,y+4,795,95,25)
    elif kind=='closing':
        c.shape(40,220,7,210,p['accent'])
        c.text(s.get('headline','下一步'),76,226,1130,152,56,p['ink'],True,display=True)
        if s.get('body'):
            c.shape(40,470,1200,126,p['tint'],kind=MSO_SHAPE.ROUNDED_RECTANGLE)
            c.text(s['body'],72,494,1140,82,23,p['secondary'])
    else:raise ValueError('Unknown layout: '+str(kind))

def build(doc,output,base,draft=False,plan_path=None,approval_path=None):
    base=Path(base);output=Path(output)
    if plan_path is None:raise ValueError('Plan approval is required: pass the exact edited plan that was reviewed.')
    if output.exists():raise ValueError('Output exists. Choose a new filename; do not overwrite the user\'s deck.')
    if doc != load(plan_path):raise ValueError('Rendering document differs from the approved plan file.')
    catalog=load(ROOT/'assets/design-catalog.json');pals=load(ROOT/'assets/palettes.json')
    errors=requirements_errors(doc.get('design',{})) if draft else design_errors(doc.get('design',{}),base)
    errors+=plan_errors(doc.get('slides',[]))
    if errors:raise ValueError('Task is not ready: '+'; '.join(errors))
    approval=approval_errors(plan_path,approval_path)
    if approval:raise ValueError('Plan is not approved for rendering: '+'; '.join(approval))
    doc,errors,report_audit=prepare_report(doc,base)
    if errors:raise ValueError('Report is not ready: '+'; '.join(errors))
    selection=doc.get('design',{}).get('selection',{})
    palid=selection.get('palette',doc.get('palette','P1'))
    if palid not in pals:raise ValueError('Unknown palette')
    template=next((t for t in catalog['templates'] if t['id']==selection.get('template',doc.get('template','T01'))),None)
    if template is None:raise ValueError('Unknown template')
    slides=doc.get('slides',[])
    if not 1<=len(slides)<=100:raise ValueError('Provide 1–100 slides')
    prs=Presentation();prs.slide_width=unit(W);prs.slide_height=unit(H)
    prs.core_properties.author='workskill contributors';prs.core_properties.title=doc.get('title','演示文稿')
    tag=doc.get('tag',catalog['scenes'][selection.get('scenario',template['scene'])]['name'])
    placements=[];known={a['id']:a for a in load(ROOT/'assets/media-library/catalog.json')['assets']}
    for idx,s in enumerate(slides,1):
        sl=prs.slides.add_slide(prs.slide_layouts[6]);c=Canvas(sl,pals[palid],doc.get('font','Microsoft YaHei'),template['style'],doc.get('display_font'))
        slide_label=report_audit['slide_labels'].get(str(idx),'')
        render_layout(c,s,idx,tag+(' · '+slide_label if slide_label else ''),draft,base)
        sl.notes_slide.notes_text_frame.text='\n'.join(s.get('sources',[]))+'\n'+report_audit['slide_notes'].get(str(idx),'')+('\n合成演示内容，非真实经营或研究数据。' if doc.get('demo') else '')
        credits=[]
        for a in s.get('assets',[]):
            if a.get('id') not in known:raise ValueError('Unknown asset '+str(a.get('id')))
            if not draft and a['id'] not in selection['assets']:raise ValueError('Used asset was not part of the selected material set')
            meta=known[a['id']]
            if not meta.get('native',{}).get('path'):raise ValueError('No native cache; convert original SVG to a PNG and use a separate image, with honest editability disclosure: '+a['id'])
            placements.append({'slide':idx,'asset':a['id'],'box':a['box'],'name':a.get('name',a['id'])})
            if meta['license'].startswith('CC-BY'):credits.append(meta['attribution'])
        if credits:c.text(' | '.join(credits),48,646,1170,32,13,pals[palid]['secondary'])
    labels=[]
    if doc.get('demo') or any(s.get('synthetic') for s in slides):labels.append(doc.get('synthetic_label','合成模板 · 示例数据，请替换后使用'))
    if draft:labels.append('设计草稿 · 待确认')
    disclosure=add_document_disclosure(prs,pals[palid],doc.get('font','Microsoft YaHei'),' · '.join(labels))
    output.parent.mkdir(parents=True,exist_ok=True)
    if placements:
        import assets
        # Explicit output-adjacent temp directory; no OS temp and no leaked base deck.
        with tempfile.TemporaryDirectory(prefix='.wb-ppt-',dir=output.parent) as td:
            intermediate=Path(td)/'native-base.pptx';prs.save(intermediate)
            assets.insert(intermediate,output,{'canvas':[W,H],'placements':placements})
    else:prs.save(output)
    return {'output':str(output),'slides':len(slides),'draft':draft,'native_materials_inserted':len(placements),
            'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'visual_validation':'not_performed_by_generator',
            'analysis_bindings_applied':len(report_audit['bindings']),'semantic_review':'required',
            'disclosure_slides':disclosure,'technical_integrity':'unverified','presentation_quality':'unverified'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--draft',action='store_true');ap.add_argument('--plan-approval',help='approval sidecar; defaults to <input>.approval.json')
    args=ap.parse_args();dest=Path(args.output)
    if dest.exists():ap.error('Output exists. Choose a new filename; do not overwrite the user\'s deck.')
    try:print(json.dumps(build(load(args.input),dest,Path(args.input).resolve().parent,args.draft,plan_path=Path(args.input).resolve(),approval_path=Path(args.plan_approval).resolve() if args.plan_approval else None),ensure_ascii=False,indent=2))
    except (ValueError,FileNotFoundError) as exc:print(str(exc),file=sys.stderr);raise SystemExit(2)
