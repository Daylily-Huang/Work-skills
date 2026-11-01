"""Native business slide layouts. All content/data come from the explicit plan.

No generated preview is used as a full-slide image. Gradient fills and layered
ellipses are editable DrawingML shapes, tables and charts are native Office objects.
"""
import copy,math
from pptx.oxml.xmlchemy import OxmlElement
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE,XL_LEGEND_POSITION
from pptx.util import Pt,Emu
from text_style import set_cjk_font
from layout_contract import validate_data
from chrome import header as _shared_header,data_table as _shared_table

def U(v):return int(v*9525)
def color(c):return c.lstrip('#')
def blend(c,t=.8):
    c=color(c);return '#'+''.join(f'{round(int(c[i:i+2],16)*(1-t)+255*t):02X}' for i in (0,2,4))
def grad(sh,a,b,angle=0):
    sp=sh._element.spPr
    for q in list(sp):
        if q.tag.split('}')[-1] in ('solidFill','gradFill','noFill'):sp.remove(q)
    g=OxmlElement('a:gradFill');g.set('rotWithShape','1');st=OxmlElement('a:gsLst')
    for pos,c in [('0',a),('100000',b)]:
        gs=OxmlElement('a:gs');gs.set('pos',pos);v=OxmlElement('a:srgbClr');v.set('val',color(c));gs.append(v);st.append(gs)
    g.append(st);line=OxmlElement('a:lin');line.set('ang',str(angle*60000));line.set('scaled','1');g.append(line)
    # DrawingML requires geometry before fill and fill before line/effects.
    outline=sp.find('{http://schemas.openxmlformats.org/drawingml/2006/main}ln')
    sp.insert(list(sp).index(outline) if outline is not None else len(sp),g)
def shadow(sh):
    sp=sh._element.spPr
    for q in list(sp):
        if q.tag.split('}')[-1]=='effectLst':sp.remove(q)
    e=OxmlElement('a:effectLst');s=OxmlElement('a:outerShdw')
    for k,v in {'blurRad':'80000','dist':'19050','dir':'5400000','algn':'ctr','rotWithShape':'0'}.items():s.set(k,v)
    c=OxmlElement('a:srgbClr');c.set('val','000000');a=OxmlElement('a:alpha');a.set('val','10000');c.append(a);s.append(c);e.append(s);sp.append(e)
def panel(c,x,y,w,h,title=None,dark=False):
    p=c.p;fill=p['primary'] if dark else p['paper'];sh=c.shape(x,y,w,h,fill,blend(p['primary'],.83),MSO_SHAPE.ROUNDED_RECTANGLE);sh.adjustments[0]=.04
    if dark:grad(sh,p['primary'],blend(p['primary'],.12),25)
    if title:
        c.shape(x+14,y+15,5,19,p['accent']);c.text(title,x+29,y+10,w-42,32,20,'#FFFFFF' if dark else p['ink'],True)
    return sh
def ribbon(c,title,x,y,w=260):
    sh=c.shape(x,y,w,36,c.p['primary'],kind=MSO_SHAPE.CHEVRON);grad(sh,c.p['primary'],c.p['secondary']);c.text(title,x+17,y+5,w-39,30,20,'#FFFFFF',True)
def table(c,heads,rows,x,y,w,h):
    # Business rows run one size smaller than the report tables.
    return _shared_table(c,heads,rows,x,y,w,h,size=13,head_h=min(44,h/(len(rows)+1)))

def bar(c,x,y,w,h,fraction,col=None,bg=None):
    if not 0<=fraction<=1:raise ValueError('Progress must be 0..1')
    c.shape(x,y,w,h,bg or c.p['tint'],kind=MSO_SHAPE.ROUNDED_RECTANGLE)
    if fraction:
        sh=c.shape(x,y,max(1,w*fraction),h,col or c.p['primary'],kind=MSO_SHAPE.ROUNDED_RECTANGLE);grad(sh,col or c.p['primary'],blend(col or c.p['primary'],.18))
def chart(c,d,x,y,w,h,kind='bar'):
    cats=d['categories'];sers=d['series']
    if not cats or not sers or any(len(s['values'])!=len(cats) or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in s['values']) for s in sers):raise ValueError('Chart data must be finite and match categories')
    types={'bar':XL_CHART_TYPE.COLUMN_CLUSTERED,'line':XL_CHART_TYPE.LINE_MARKERS,'donut':XL_CHART_TYPE.DOUGHNUT,'horizontal':XL_CHART_TYPE.BAR_CLUSTERED,'stacked':XL_CHART_TYPE.COLUMN_STACKED,'combo':XL_CHART_TYPE.COLUMN_CLUSTERED}
    data=CategoryChartData();data.categories=cats
    for sr in sers:data.add_series(sr['name'],sr['values'])
    sh=c.s.shapes.add_chart(types[kind],U(x),U(y),U(w),U(h),data);ch=sh.chart
    ch.has_legend=kind=='donut' or len(sers)>1
    ch.has_title=False
    if ch.has_legend:ch.legend.position=XL_LEGEND_POSITION.BOTTOM;ch.legend.font.size=Pt(11);set_cjk_font(ch.legend.font,c.font);ch.legend.include_in_layout=False
    ch.chart_style=2
    if kind!='donut':
        ch.plots[0].has_data_labels=True;set_cjk_font(ch.plots[0].data_labels.font,c.font);ch.plots[0].data_labels.font.size=Pt(11)
    cols=[c.p['primary'],c.p['accent'],c.p['secondary'],blend(c.p['primary'],.5)]
    for i,s in enumerate(ch.series):
        if hasattr(s,'invert_if_negative'):s.invert_if_negative=False
        s.format.fill.solid();s.format.fill.fore_color.rgb=__import__('pptx').dml.color.RGBColor.from_string(color(cols[i%4]));s.format.line.fill.background()
        if kind in ('line','combo'):s.format.line.color.rgb=__import__('pptx').dml.color.RGBColor.from_string(color(cols[i%4]));s.format.line.width=Pt(2)
        if kind=='combo':
            try:s.smooth=False
            except (AttributeError,ValueError):pass
        if kind=='donut':
            for j,pt in enumerate(s.points):pt.format.fill.solid();pt.format.fill.fore_color.rgb=__import__('pptx').dml.color.RGBColor.from_string(color(cols[j%4]))
    if kind!='donut':
        for a in (ch.category_axis,ch.value_axis):set_cjk_font(a.tick_labels.font,c.font);a.tick_labels.font.size=Pt(11)
        axis_values=sers[0]['values'] if kind=='combo' else [v for sr in sers for v in sr['values']]
        ch.value_axis.minimum_scale=min(0,min(axis_values)*1.1)
    else:ch.plots[0].hole_size=70
    if kind=='combo':
        if len(sers)!=2:raise ValueError('Combo requires two series')
        secondary_max=d.get('secondary_max')
        if not isinstance(secondary_max,(int,float)) or isinstance(secondary_max,bool) or not math.isfinite(secondary_max) or secondary_max<=0 or secondary_max<max(sers[1]['values']):
            raise ValueError('secondary_max must be positive and cover all secondary series values; do not clip the data')
        area=ch._chartSpace.chart.plotArea;bc=area.find('{http://schemas.openxmlformats.org/drawingml/2006/chart}barChart');ns='{http://schemas.openxmlformats.org/drawingml/2006/chart}'
        sr=bc.findall(ns+'ser')[1];bc.remove(sr);lc=OxmlElement('c:lineChart');g=OxmlElement('c:grouping');g.set('val','standard');lc.append(g);lc.append(sr)
        # Move second native series to its own percentage axis; embedded workbook is retained.
        catsrc=area.find(ns+'catAx');valsrc=area.find(ns+'valAx');catid=catsrc.find(ns+'axId').get('val')
        for id in ('810001','810002'):a=OxmlElement('c:axId');a.set('val',id);lc.append(a)
        area.insert(list(area).index(catsrc),lc)
        ca=copy.deepcopy(catsrc);va=copy.deepcopy(valsrc)
        ca.find(ns+'axId').set('val','810001');ca.find(ns+'crossAx').set('val','810002');ca.find(ns+'delete').set('val','1')
        va.find(ns+'axId').set('val','810002');va.find(ns+'crossAx').set('val','810001');va.find(ns+'axPos').set('val','r')
        nf=va.find(ns+'numFmt')
        if nf is None:nf=OxmlElement('c:numFmt');va.append(nf)
        nf.set('formatCode','0%');nf.set('sourceLinked','0')
        scaling=va.find(ns+'scaling');mx=OxmlElement('c:max');mx.set('val',str(d['secondary_max']));scaling.append(mx)
        mn=scaling.find(ns+'min')
        if mn is None:mn=OxmlElement('c:min');scaling.append(mn)
        mn.set('val',str(min(0,min(sers[1]['values'])*1.1)))
        cross=va.find(ns+'crosses')
        if cross is not None:cross.set('val','max')
        for grid in va.findall(ns+'majorGridlines'):va.remove(grid)
        area.append(ca);area.append(va)
    return sh
def ring(c,x,y,w,h,title,labels,strong=False):
    p=c.p;depth=h*.36;top=h*.38
    # Layered editable shapes form a curved front and an illuminated top.
    low=c.shape(x,y+depth,w,top,p['primary'],kind=MSO_SHAPE.OVAL);grad(low,p['primary'],blend(p['primary'],.3),90)
    front=c.shape(x,y+top/2,w,depth,p['primary'] if strong else p['tint']);grad(front,blend(p['primary'],.1 if strong else .8),p['primary'] if strong else blend(p['primary'],.96),90)
    face=c.shape(x,y,w,top,blend(p['primary'],.94),blend(p['primary'],.55),MSO_SHAPE.OVAL);grad(face,'#FFFFFF',p['tint'],90);shadow(low)
    c.text(title,x+10,y+5,w-20,34,23,p['primary'],True,PP_ALIGN.CENTER)
    if labels:
        step=w/len(labels)
        for i,t in enumerate(labels):
            c.text(t,x+i*step+5,y+top+5,step-10,39,18,'#FFFFFF' if strong else p['primary'],True,PP_ALIGN.CENTER)
            if i:c.line(x+i*step,y+top,x+i*step,y+top+31,blend(p['primary'],.55),.6)
def cards(c,items,x,y,w,h,cols=2):
    rows=math.ceil(len(items)/cols);cw=(w-16*(cols-1))/cols;ch=(h-14*(rows-1))/rows
    for i,it in enumerate(items):
        xx=x+(i%cols)*(cw+16);yy=y+(i//cols)*(ch+14)
        c.shape(xx,yy,cw,ch,c.p['tint'],kind=MSO_SHAPE.ROUNDED_RECTANGLE)
        head=c.shape(xx+10,yy+9,cw-20,32,c.p['primary'],kind=MSO_SHAPE.ROUNDED_RECTANGLE);grad(head,c.p['primary'],blend(c.p['primary'],.22))
        c.text((f'{i+1:02}  ' if len(items)>1 else '')+it['title'],xx+19,yy+13,cw-38,29,19,'#FFFFFF',True)
        c.text(it['body'],xx+15,yy+49,cw-30,ch-52,18 if ch>110 else 14,c.p['ink'])
def kpis(c,items,x,y,w,h):
    step=w/len(items)
    for i,it in enumerate(items):
        xx=x+i*step;dark=i==0;panel(c,xx,y,step-12,h,dark=dark)
        c.text(it['title'],xx+15,y+11,step-40,28,18,'#FFFFFF' if dark else c.p['ink'],True)
        c.text(it['value'],xx+15,y+42,step-35,60,40,'#FFFFFF' if dark else c.p['primary'],True)
def chevrons(c,items,x,y,w,h):
    step=w/len(items)
    for i,it in enumerate(items):
        sh=c.shape(x+i*step,y,step-5,h,c.p['primary'],kind=MSO_SHAPE.CHEVRON);grad(sh,c.p['primary'],blend(c.p['primary'],i*.08))
        sh.adjustments[0]=.16
        c.text(it,x+i*step+10,y+12,step-24,h-16,16 if step<160 else 20,'#FFFFFF',True,PP_ALIGN.CENTER)
def frame(c,s,idx,tag,draft):
    # One masthead for the whole deck; see chrome.py.
    _shared_header(c,s['title'],tag,idx,draft)

def render(c,s,idx,tag,draft,base):
    d=s.get('data')
    if not isinstance(d,dict):raise ValueError('Business layout requires explicit data; no implicit demo facts')
    errors=validate_data(s,c.style)
    if errors:raise ValueError('; '.join(errors))
    p=c.p;k=s['layout'].removeprefix('office_');frame(c,s,idx,tag,draft)
    items=d.get('items',[]);steps=d.get('steps',[]);metrics=d.get('metrics',[]);rows=d.get('rows',[]);heads=d.get('headers',[]);ch=d.get('chart')
    if k=='cover':
        c.text(d['headline'],40,150,700,190,50,p['primary'],True,display=True)
        c.text(d['subtitle'],43,352,680,64,22,p['ink'])
        c.shape(40,428,120,4,p['accent']);chevrons(c,steps[:4],40,462,690,64)
        c.text(d['meta'],42,566,670,58,18,p['secondary'])
        if c.style.startswith('red'):
            for i in range(3):ring(c,790-i*22,190+i*125,360+i*44,100,items[i]['title'],[],i==2)
        elif c.style.startswith('black'):
            for i,m in enumerate(metrics[:3]):panel(c,800,160+i*157,410,140,dark=i!=1);c.text(m['title'],821,178+i*157,360,35,21,'#FFFFFF' if i!=1 else p['ink'],True);c.text(m['value'],821,216+i*157,360,84,48,'#FFFFFF' if i!=1 else p['accent'],True)
        else:
            panel(c,800,153,413,455);ribbon(c,'关键工作节点',815,170,360)
            for i,it in enumerate(items[:4]):
                y=241+i*79;c.shape(830,y+8,23,23,p['primary'],kind=MSO_SHAPE.OVAL)
                if i<3:c.line(841,y+30,841,y+86,p['secondary'],2)
                c.text(it['title'],875,y,315,32,23,p['primary'],True);c.text(it['body'].split('\n')[0],875,y+35,310,33,16,p['secondary'])
    elif k=='summary':
        kpis(c,metrics,32,145,1216,108)
        panel(c,32,275,760,385,d.get('panel_title','核心指标趋势'));chart(c,ch,49,321,720,312,'combo')
        panel(c,810,275,438,385,'重点工作与判断');cards(c,items[:3],824,323,410,318,1)
    elif k=='scorecard':
        for i,it in enumerate(items[:4]):
            xx=32+(i%2)*616;yy=145+(i//2)*187;panel(c,xx,yy,600,170,it['title'])
            m=metrics[i];c.text(m['value'],xx+22,yy+54,170,62,42,p['primary'],True);c.text(it['body'],xx+220,yy+62,355,74,21)
            bar(c,xx+22,yy+139,550,12,d['score_progress'][i])
        table(c,heads,rows[:3],32,543,1216,115)
    elif k=='gantt':
        chevrons(c,steps[:5],32,144,1216,49)
        x=198;y=219;w=1050;cw=w/12;rh=47
        c.shape(32,y,1216,35,p['primary']);c.text('项目任务',43,y+5,148,30,18,'#FFFFFF',True)
        for j in range(12):c.text(f'{j+1}月',x+j*cw,y+5,cw,29,17,'#FFFFFF',True,PP_ALIGN.CENTER)
        for i,row in enumerate(d['schedule']):
            yy=y+35+i*rh;c.shape(32,yy,1216,rh,p['tint'] if i%2==0 else '#FFFFFF');c.text(row['name'],42,yy+10,150,32,19,p['primary'],True)
            for j in range(13):c.line(x+j*cw,yy,x+j*cw,yy+rh,blend(p['secondary'],.72),.5)
            start,end,progress=row['start'],row['end'],row['progress']
            if not (1<=start<=end<=12):raise ValueError('Gantt month outside 1..12')
            xx=x+(start-1)*cw+7;ww=(end-start+1)*cw-14;bar(c,xx,yy+13,ww,21,progress)
            c.text(f'{progress:.0%}',xx+max(0,ww-62),yy+13,min(60,ww),27,16,'#FFFFFF' if progress==1 else p['primary'],True,PP_ALIGN.CENTER)
        panel(c,32,565,780,99,'交付节点');c.text(d['milestones'],54,608,740,42,20,p['primary'],True)
        panel(c,830,565,418,99);c.text(d['progress_label'],851,578,370,32,20,p['primary'],True);bar(c,851,621,367,18,d['progress'])
    elif k=='swimlane':
        chevrons(c,steps[:5],210,145,1038,45)
        for i,it in enumerate(items[:4]):
            yy=211+i*109;c.shape(32,yy,1216,97,p['tint'] if i%2==0 else '#FFFFFF');c.shape(32,yy,160,97,p['primary']);c.text(it['title'],45,yy+31,135,37,21,'#FFFFFF',True)
            for j in range(4):
                xx=217+j*255;panel(c,xx,yy+13,232,70);c.text(d['lane_tasks'][i][j],xx+10,yy+18,212,60,18,p['primary'],True,PP_ALIGN.CENTER)
                if j<3:c.shape(xx+234,yy+40,15,13,p['accent'],kind=MSO_SHAPE.RIGHT_ARROW)
    elif k=='milestone':
        chevrons(c,steps[:5],32,145,1216,52);c.line(110,286,1180,286,p['secondary'],3)
        for i,it in enumerate(items[:5]):
            x=45+i*244;c.shape(x+74,267,38,38,p['primary'],kind=MSO_SHAPE.OVAL);c.text(f'{i+1:02}',x+76,270,35,32,18,'#FFFFFF',True,PP_ALIGN.CENTER)
            c.text(it['title'],x,219,218,35,21,p['primary'],True,PP_ALIGN.CENTER);panel(c,x,331,222,164);c.text(it['body'],x+14,350,192,130,19)
        table(c,heads,rows[:3],32,530,1216,128)
    elif k=='house':
        roof=c.shape(110,145,1060,118,p['primary'],kind=MSO_SHAPE.ISOSCELES_TRIANGLE);grad(roof,p['primary'],p['secondary'])
        c.text(d['headline'],320,215,640,40,25,'#FFFFFF',True,PP_ALIGN.CENTER)
        for i,it in enumerate(items[:4]):cards(c,[it],61+i*304,281,281,293,1)
        c.shape(52,596,1176,61,p['primary']);c.text(d['footer_message'],75,612,1130,38,23,'#FFFFFF',True,PP_ALIGN.CENTER)
    elif k in ('wbs','org','six_pillars'):
        top=c.shape(330,147,620,60,p['primary'],kind=MSO_SHAPE.PENTAGON if k=='house' else MSO_SHAPE.ROUNDED_RECTANGLE);grad(top,p['primary'],p['secondary']);c.text(d['headline'],345,162,590,36,25,'#FFFFFF',True,PP_ALIGN.CENTER)
        c.line(640,207,640,241,p['primary'],2);c.line(140,241,1140,241,p['primary'],2)
        n=4 if k=='house' else (6 if k=='six_pillars' else 3);step=1216/n
        for i,it in enumerate(items[:n]):
            xx=32+i*step;c.line(xx+step/2,241,xx+step/2,272,p['primary'],2)
            cards(c,[it],xx+5,276,step-10,300,1)
        c.shape(32,603,1216,55,p['primary']);c.text(d['footer_message'],50,615,1180,35,23,'#FFFFFF',True,PP_ALIGN.CENTER)
    elif k=='resource':
        panel(c,32,145,690,330,'资源投入与分配');table(c,heads,rows,48,199,657,259)
        panel(c,742,145,506,330,'投入结构');chart(c,d['allocation_chart'],755,190,478,266,'donut')
        cards(c,items[:3],32,497,1216,163,3)
    elif k=='delivery':
        kpis(c,metrics[:3],32,145,1216,106);table(c,heads,rows,32,278,800,280)
        panel(c,851,278,397,280,'阶段完成情况');chart(c,d['donut'],883,323,330,210,'donut')
        chevrons(c,steps[:5],32,588,1216,65)
    elif k=='customer':
        panel(c,32,145,727,360,'用户分层与运营重点')
        for i,it in enumerate(items[:4]):
            xx=50+(i%2)*350;yy=198+(i//2)*145;cards(c,[it],xx,yy,337,133,1)
        panel(c,779,145,469,360,'分层用户结构');chart(c,d['segment_chart'],795,192,437,291,'donut')
        table(c,heads,rows[:3],32,529,1216,129)
    elif k in ('risk','quadrant'):
        panel(c,32,145,630,399,d['matrix_title']);x=77;y=212;ww=528;hh=275
        c.line(x+ww/2,y,x+ww/2,y+hh,p['primary'],1);c.line(x,y+hh/2,x+ww,y+hh/2,p['primary'],1)
        for i,it in enumerate(items[:4]):
            xx=x+(i%2)*ww/2;yy=y+(i//2)*hh/2;c.shape(xx+6,yy+7,ww/2-12,hh/2-14,p['tint']);c.text(it['title'],xx+18,yy+20,ww/2-36,35,22,p['primary'],True);c.text(it['body'],xx+18,yy+62,ww/2-36,59,17)
        panel(c,681,145,567,399,'问题、影响与应对');table(c,heads,rows[:5],696,200,536,325)
        c.text(d['footer_message'],39,579,1200,70,23,p['primary'],True)
    elif k=='roadmap':
        quarters=d['periods'];step=1040/len(quarters)
        for j,q in enumerate(quarters):ribbon(c,q,206+j*step,147,step-10)
        for i,it in enumerate(items[:3]):
            yy=212+i*139;c.shape(32,yy,162,121,p['primary']);c.text(it['title'],45,yy+41,133,47,22,'#FFFFFF',True,PP_ALIGN.CENTER)
            for j in range(len(quarters)):
                xx=206+j*step;panel(c,xx,yy,step-12,121);c.text(d['roadmap_cells'][i][j],xx+14,yy+21,step-40,86,19,p['primary'],True)
    elif k=='sop':
        chevrons(c,steps[:5],32,146,1216,70)
        for i,it in enumerate(items[:5]):
            xx=32+i*244;panel(c,xx,240,228,254);c.text(it['title'],xx+15,258,198,45,22,p['primary'],True);c.text(it['body'],xx+15,317,198,151,20)
        table(c,heads,rows[:3],32,522,1216,135)
    elif k=='portfolio':
        for i,it in enumerate(items[:4]):
            xx=32+(i%2)*616;yy=145+(i//2)*260;panel(c,xx,yy,600,243,it['title']);c.text(it['body'],xx+20,yy+61,560,73,21)
            c.text(d['project_status'][i]['label'],xx+20,yy+145,560,38,21,p['primary'],True);bar(c,xx+20,yy+200,550,20,d['project_status'][i]['progress'])
    elif k=='growth':
        kpis(c,metrics[:3],32,144,880,94)
        panel(c,32,252,880,222,d.get('panel_title','月度成交与转化趋势'));chart(c,ch,42,293,852,174,'combo')
        panel(c,32,490,438,172,'重点项目推进');table(c,heads,rows[:3],41,536,421,117)
        panel(c,486,490,426,172,'会员增长闭环')
        for n,(xx,yy) in enumerate([(503,540),(718,540),(718,605),(503,605)]):
            c.shape(xx,yy,173,40,blend(p['accent'],.97),p['accent'],MSO_SHAPE.ROUNDED_RECTANGLE);c.text(steps[n],xx+10,yy+9,153,30,18,p['accent'],True,PP_ALIGN.CENTER)
        c.shape(683,552,26,14,p['accent'],kind=MSO_SHAPE.RIGHT_ARROW);c.shape(797,583,14,17,p['accent'],kind=MSO_SHAPE.DOWN_ARROW);c.shape(683,617,26,14,p['accent'],kind=MSO_SHAPE.LEFT_ARROW);c.shape(581,583,14,17,p['accent'],kind=MSO_SHAPE.UP_ARROW)
        for i,m in enumerate(d['side_metrics']):
            yy=144+i*177;sh=panel(c,932,yy,316,164,dark=i!=1)
            if i==1:grad(sh,p['accent'],blend(p['accent'],.05))
            c.text(m['title'],948,yy+12,282,33,19,'#FFFFFF',True);c.text(m['value'],948,yy+51,282,63,43,'#FFFFFF',True);c.text(m['body'],949,yy+118,280,36,16,'#FFFFFF')
    elif k in ('retention','training'):
        panel(c,32,145,780,277,'阶段表现与执行进度');chart(c,d['donut'],42,193,330,215,'donut')
        c.text(d['headline'],385,207,405,67,35,p['primary'],True);c.text(d['subtitle'],385,294,405,100,21)
        panel(c,832,145,416,277,'投入与产出');kpis(c,metrics[:2],847,210,390,125)
        table(c,heads,rows,32,446,780,213);cards(c,items[:2],832,446,416,213,1)
    elif k=='sales':
        kpis(c,metrics,32,144,1216,100);panel(c,32,265,755,394,'目标与实际对比');chart(c,d['comparison_chart'],43,309,728,335)
        panel(c,805,265,443,394,'区域贡献');chart(c,d['ranking_chart'],819,315,415,323,'horizontal')
    elif k=='finance':
        kpis(c,metrics[:3],32,145,1216,100);panel(c,32,263,800,250,'收支变动分解')
        vals=d['waterfall'];maxv=max(abs(r['value']) for r in vals);step=750/len(vals)
        c.line(65,420,801,420,p['secondary'],.8)
        for i,v in enumerate(vals):
            hh=abs(v['value'])/maxv*80;xx=62+i*step;col=p['primary'] if v['value']>=0 else p['accent'];positive=v['value']>=0
            c.shape(xx+10,420-hh if positive else 420,step-28,hh,col);c.text(str(v['value']),xx,393-hh if positive else 420+hh,step-8,27,18,col,True,PP_ALIGN.CENTER);c.text(v['name'],xx,481,step-7,29,17,align=PP_ALIGN.CENTER)
        panel(c,850,263,398,250,'费用结构');chart(c,d['allocation_chart'],862,301,374,204,'donut');table(c,heads,rows[:3],32,535,1216,124)
    elif k=='funnel':
        vals=d['funnel'];maxv=vals[0]['value']
        for i,row in enumerate(vals):
            ww=600*(.38+.62*row['value']/maxv);xx=32+(620-ww)/2;yy=147+i*96;sh=c.shape(xx,yy,ww,75,p['primary'] if i%2==0 else p['secondary'],kind=MSO_SHAPE.TRAPEZOID);grad(sh,p['primary'],blend(p['primary'],i*.12));c.text(f"{row['name']}  {row['value']:,}",xx+20,yy+21,ww-40,38,24,'#FFFFFF',True,PP_ALIGN.CENTER)
        cards(c,items[:3],692,148,556,292,1);table(c,heads,rows[:4],692,461,556,198)
    elif k=='channel':
        panel(c,32,145,745,350,'渠道获客表现');chart(c,d['ranking_chart'],43,194,720,280,'horizontal')
        panel(c,795,145,453,350,'效率与费用');table(c,heads,rows[:5],809,197,425,278);cards(c,items[:3],32,517,1216,142,3)
    elif k=='supplychain':
        # Editable hub-and-spoke, with explicit connectors behind modules.
        cx,cy=645,369
        positions=[(115,160),(480,145),(880,160),(115,470),(480,485),(880,470)]
        for xx,yy in positions:c.line(cx,cy,xx+140,yy+60,p['secondary'],2)
        for (xx,yy),it in zip(positions,items):cards(c,[it],xx,yy,280,134,1)
        hub=c.shape(490,296,310,140,p['primary'],kind=MSO_SHAPE.OVAL);grad(hub,p['primary'],blend(p['primary'],.15));c.text(d['headline'],510,337,270,65,28,'#FFFFFF',True,PP_ALIGN.CENTER)
    elif k=='talent_rings':
        cards(c,items[:4],32,148,535,510,1)
        for i,it in enumerate(items[:4]):
            xx=630+(i%2)*20;yy=149+i*127;ww=570-(i%2)*40
            donut=c.shape(xx,yy,ww,90,p['primary'],kind=MSO_SHAPE.DONUT);donut.adjustments[0]=.18;grad(donut,blend(p['primary'],.9),p['primary'],90);shadow(donut)
            c.text(it['title'],xx+80,yy+22,ww-160,42,26,p['primary'],True,PP_ALIGN.CENTER)
            c.text(d['talent_nodes'][i],xx+40,yy+98,ww-80,25,16,p['primary'],True,PP_ALIGN.CENTER)
    elif k=='pyramid':
        cards(c,items[:4],32,148,535,393,2)
        c.text(d['footer_message'],44,574,511,74,21,p['primary'],True)
        for i,it in enumerate(reversed(items[:4])):
            ww=235+i*105;xx=660+(540-ww)/2;yy=158+i*124
            block=c.shape(xx,yy,ww,103,p['primary'],kind=MSO_SHAPE.TRAPEZOID);grad(block,p['primary'],blend(p['primary'],.15+i*.1))
            c.text(it['title'],xx+25,yy+30,ww-50,42,25,'#FFFFFF',True,PP_ALIGN.CENTER)
        c.text(d['pyramid_caption'],660,654,540,25,16,p['secondary'],align=PP_ALIGN.CENTER)
    elif k=='tiers':
        cards(c,items[:6],32,148,580,510,2)
        names=d['tier_titles'];labels=d['tier_labels'];n=len(names)
        if k=='tiers':
            for i in range(n-1):
                yy=156+i*(468/n);connector=c.shape(915,yy+85,42,115,p['accent'],kind=MSO_SHAPE.TRAPEZOID);grad(connector,blend(p['accent'],.9),blend(p['accent'],.55),90)
        for i,name in enumerate(names):
            ww=(530-i*45) if k=='pyramid' else (440+i*35);xx=663+(545-ww)/2;yy=156+i*(468/n)
            ring(c,xx,yy,ww,136 if n==3 else 105,name,labels[i],i==n-1)
        c.shape(661,619,580,39,p['accent']);c.text(d['footer_message'],674,625,554,32,20,'#FFFFFF',True,PP_ALIGN.CENTER)
    elif k=='wings':
        ring(c,410,179,460,137,d['headline'],d['tier_labels'][0],True)
        for xx,it in zip((32,912),items[:2]):cards(c,[it],xx,238,335,285,1)
        c.shape(358,358,61,44,p['accent'],kind=MSO_SHAPE.RIGHT_ARROW);c.shape(861,358,61,44,p['accent'],kind=MSO_SHAPE.LEFT_ARROW)
        ring(c,384,439,510,112,d['tier_titles'][1],d['tier_labels'][1],False);c.shape(32,604,1216,54,p['primary']);c.text(d['footer_message'],52,616,1175,36,23,'#FFFFFF',True,PP_ALIGN.CENTER)
    elif k=='u_stages':
        pts=[(80,150),(700,150),(700,420),(80,420)]
        c.shape(584,205,110,38,p['accent'],kind=MSO_SHAPE.RIGHT_ARROW);c.shape(936,341,38,65,p['accent'],kind=MSO_SHAPE.DOWN_ARROW);c.shape(583,480,110,38,p['accent'],kind=MSO_SHAPE.LEFT_ARROW)
        for i,((xx,yy),it) in enumerate(zip(pts,items[:4])):ring(c,xx,yy,480,140,it['title'],[],False);c.text(it['body'],xx+34,yy+143,417,75,20)
    elif k=='value_chain':
        chevrons(c,steps[:5],32,153,1216,75)
        for i,it in enumerate(items[:5]):
            xx=32+i*244;ring(c,xx+4,270,218,120,it['title'],[],False);c.text(it['body'],xx+15,411,198,121,20)
        c.shape(32,595,1216,62,p['primary']);c.text(d['footer_message'],48,611,1183,40,25,'#FFFFFF',True,PP_ALIGN.CENTER)
    elif k=='before_after':
        for j,title in enumerate(d['compare_titles']):
            xx=32+j*620;ribbon(c,title,xx,147,595)
            for i,it in enumerate(items[j*3:(j+1)*3]):
                yy=214+i*141;cards(c,[it],xx,yy,595,126,1)
        c.shape(608,366,52,45,p['accent'],kind=MSO_SHAPE.RIGHT_ARROW)
    elif k=='cycle':
        pts=[(504,148),(878,334),(504,517),(126,334)]
        for i,(xx,yy) in enumerate(pts):
            nx,ny=pts[(i+1)%4];c.line(xx+135,yy+58,nx+135,ny+58,p['accent'],3)
        for (xx,yy),it in zip(pts,items[:4]):cards(c,[it],xx,yy,275,137,1)
        c.shape(475,324,330,158,p['primary'],kind=MSO_SHAPE.OVAL);c.text(d['headline'],495,370,290,75,29,'#FFFFFF',True,PP_ALIGN.CENTER)
    elif k in ('actions','review'):
        y=146
        if steps:
            chevrons(c,steps[:5],32,y,1216,59);y=215
        if k=='actions':
            # Height follows the row count; a fixed tall table stretches every row and leaves the page bottom bare.
            body_h=44+105*len(rows)
            height=min(body_h,299) if items else min(body_h,650-y)
            top=y if items else y+max(0,(650-y-height)//2)
            table(c,heads,rows,32,top,1216,height)
            if items:cards(c,items[:3],32,526,1216,130,3)
        else:
            has_footer=bool(d.get('headline') or d.get('footer_message'))
            height=260
            top=y+12 if has_footer else y+12+max(0,(650-(y+12)-height)//2)
            cards(c,items,32,top,1216,height,min(3,len(items)))
            if has_footer:
                panel(c,32,501,1216,157,d.get('headline'))
                if d.get('footer_message'):c.text(d['footer_message'],53,554,1173,72,24,p['primary'],True)
    else:raise ValueError('Unknown business layout '+k)
