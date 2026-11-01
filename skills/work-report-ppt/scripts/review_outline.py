"""Deterministic user-review outline shared by authoring and approval validation."""
import json

def render_text(bound, audit):
    narrative = bound['narrative']
    lines = ['# '+bound.get('title','工作汇报'), '', '决策目标：'+narrative['decision_goal'],
             '听众问题：'+narrative['audience_question'], '核心信息：'+narrative['key_takeaway'], '', '## 发现与证据', '']
    labels={'observation':'观察事实','hypothesis':'待验证假说','explanation':'材料支持的解释（须核对）'}
    for item in narrative['findings']:
        lines += [f'- [{item["id"]}] {labels[item["kind"]]}：{item["text"]}；依据：'+', '.join(item['evidence_ids']),
                  '  范围：'+item['scope']+'；比较基准：'+', '.join(item['comparisons'])]
        for field,label in [('validation','验证方式'),('limits','适用边界')]:
            if item.get(field): lines += ['  '+label+'：'+item[field]]
    lines += ['', '## 行动和请求', '']
    status={'proposed':'待确认','agreed':'已确认'}
    for item in narrative['actions']:
        lines += [f'- [{item["id"]}] {status[item["status"]]}：{item["text"]}；{item["owner"]}；{item["due"]}；验收：{item["success_criteria"]}',
                  '  前提：'+'；'.join(item['preconditions']), '  反证／回退条件：'+item['falsifier'],
                  '  可能副作用：'+'；'.join(item['side_effects'])]
    for item in narrative['requests']:
        lines += [f'- [{item["id"]}] {status[item["status"]]}：{item["text"]}', '  决策问题：'+item['decision_question']]
        for option in item['options']:
            lines += ['  选项：'+option['text']+'；条件：'+option['condition']+'；后果：'+option['consequence']]
        lines += ['  决定前补证：'+'；'.join(item['evidence_needed'])]
    lines += ['', '## 逐页计划', '']
    for index, slide in enumerate(bound['slides'],1):
        lines += [f'### {index}. {slide["title"]}', '', '用途：'+slide['purpose'],
                  '核心信息：'+audit.get('slide_messages',{}).get(str(index),''),
                  '版式：'+slide['layout']+'；理由：'+slide['layout_reason'],
                  '素材：'+(', '.join(a.get('id','') for a in slide.get('assets',[])) or '不使用'),
                  audit['slide_notes'].get(str(index),'')]
        content = {k:v for k,v in slide.items() if k in ('data','items','chart','columns','rows','headline','body','insight','unit','image','caption','subtitle','meta')}
        if content: lines += ['页面内容（含绑定后的数值）：','```json', json.dumps(content,ensure_ascii=False,indent=2),'```']
        lines += ['']
    lines += ['## 检查边界', '', '此提纲核查引用位置、结构和绑定计算；仍需逐项核对语义、原始业务真实性及未绑定数字。批准记录只保存用户真实确认，不能证明确认的真实性。','']
    return '\n'.join(lines)
