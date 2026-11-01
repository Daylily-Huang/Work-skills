"""Fields actually rendered by each office layout; no dummy KPI/chart required."""
FIELDS = {
    'cover': 'headline subtitle steps meta items',
    'summary': 'metrics chart items',
    'scorecard': 'items metrics score_progress headers rows',
    'gantt': 'steps schedule milestones progress_label progress',
    'swimlane': 'steps items lane_tasks',
    'milestone': 'steps items headers rows',
    'house': 'headline items footer_message',
    'wbs': 'headline items footer_message', 'org': 'headline items footer_message',
    'six_pillars': 'headline items footer_message',
    'resource': 'headers rows allocation_chart items',
    'delivery': 'metrics headers rows donut steps',
    'customer': 'items segment_chart headers rows',
    'risk': 'matrix_title items headers rows footer_message',
    'quadrant': 'matrix_title items headers rows footer_message',
    'roadmap': 'periods items roadmap_cells',
    'sop': 'steps items headers rows',
    'portfolio': 'items project_status',
    'growth': 'metrics chart headers rows steps side_metrics',
    'retention': 'donut headline subtitle metrics headers rows items',
    'training': 'donut headline subtitle metrics headers rows items',
    'sales': 'metrics comparison_chart ranking_chart',
    'finance': 'metrics waterfall allocation_chart headers rows',
    'funnel': 'funnel items headers rows',
    'channel': 'ranking_chart headers rows items',
    'supplychain': 'items headline',
    'talent_rings': 'items talent_nodes',
    'pyramid': 'items footer_message pyramid_caption',
    'tiers': 'items tier_titles tier_labels footer_message',
    'wings': 'headline tier_labels items tier_titles footer_message',
    'u_stages': 'items', 'value_chain': 'steps items footer_message',
    'before_after': 'compare_titles items',
    'cycle': 'items headline',
    'actions': 'headers rows',
    'review': 'items',
}
ITEM_CAPS = {'cover':4, 'summary':3, 'scorecard':4, 'swimlane':4, 'milestone':5,
             'house':4, 'wbs':3, 'org':3, 'six_pillars':6, 'resource':3, 'customer':4,
             'risk':4, 'quadrant':4, 'roadmap':3, 'sop':5, 'portfolio':4,
             'retention':2, 'training':2, 'funnel':3, 'channel':3, 'supplychain':6,
             'talent_rings':4, 'pyramid':4, 'tiers':6, 'wings':2, 'u_stages':4,
             'value_chain':5, 'before_after':6, 'cycle':4, 'actions':3, 'review':3}
ROW_CAPS = {'scorecard':3, 'milestone':3, 'customer':3, 'risk':5, 'quadrant':5,
            'sop':3, 'growth':3, 'finance':3, 'funnel':4, 'channel':5}

def required_fields(layout, style=''):
    kind = layout.removeprefix('office_')
    if kind not in FIELDS: raise ValueError('Unknown business layout '+kind)
    fields = set(FIELDS[kind].split())
    if kind == 'cover':
        fields.discard('items')
        fields.add('metrics' if style.startswith('black') else 'items')
    return fields

def validate_data(slide, style=''):
    layout = slide.get('layout', '')
    if not layout.startswith('office_'): return []
    kind = layout.removeprefix('office_')
    try: required = required_fields(layout, style)
    except ValueError as e: return [str(e)]
    data = slide.get('data')
    if not isinstance(data, dict): return ['Business layout requires explicit data.']
    missing = required - data.keys()
    if missing: return ['Business layout '+layout+' is missing rendered fields: '+', '.join(sorted(missing))]
    errors = []
    for key in required & {'items','steps','metrics','rows','headers','schedule','lane_tasks','periods',
                            'roadmap_cells','project_status','side_metrics','waterfall','funnel',
                            'talent_nodes','tier_titles','tier_labels','compare_titles'}:
        value = data[key]
        if not isinstance(value, list) or not value:
            errors.append(layout+': '+key+' must be a nonempty list; do not invent placeholders.')
    if errors: return errors
    caps = {}
    if 'items' in required: caps['items'] = ITEM_CAPS.get(kind,6)
    if 'steps' in required: caps['steps'] = 4 if kind in ('cover','growth') else 5
    if kind in ROW_CAPS: caps['rows'] = ROW_CAPS[kind]
    if kind in ('delivery','growth','finance') or (kind=='cover' and style.startswith('black')): caps['metrics']=3
    if kind in ('retention','training'): caps['metrics']=2
    if kind=='scorecard': caps['metrics']=4
    if kind=='growth': caps['side_metrics']=3
    if kind=='gantt': caps['schedule']=6
    if kind=='tiers': caps['tier_titles']=4
    if kind=='before_after': caps['compare_titles']=2
    if kind=='wings': caps.update(tier_titles=2,tier_labels=2)
    if kind=='roadmap': caps['periods']=4
    if kind=='funnel': caps['funnel']=5
    for key, cap in caps.items():
        if isinstance(data.get(key),list) and len(data[key])>cap:
            errors.append(f'{layout}: {key} exceeds capacity {cap}; split the page, never silently truncate.')
    if 'items' in required and any(not isinstance(v,dict) or not isinstance(v.get('title'),str) or not isinstance(v.get('body'),str) for v in data['items']):
        errors.append(layout+': items need title/body strings.')
    if 'headers' in required and any(not isinstance(row,list) or len(row)!=len(data['headers']) for row in data['rows']):
        errors.append(layout+': rows must match headers.')
    if kind in ('swimlane','roadmap'):
        key = 'lane_tasks' if kind=='swimlane' else 'roadmap_cells'
        width = 4 if kind=='swimlane' else len(data['periods'])
        if len(data[key])!=len(data['items']) or any(not isinstance(row,list) or len(row)!=width for row in data[key]):
            errors.append(layout+': '+key+' must align with item count and displayed columns.')
    if kind=='growth' and len(data['steps'])!=4: errors.append('office_growth needs four actual cycle steps.')
    if kind=='scorecard' and (len(data['metrics'])!=len(data['items']) or len(data['score_progress'])!=len(data['items'])):
        errors.append('office_scorecard metrics/progress must align with items.')
    if kind=='portfolio' and len(data['project_status'])!=len(data['items']):
        errors.append('office_portfolio status must align with items.')
    if kind=='talent_rings' and len(data['talent_nodes'])!=len(data['items']):
        errors.append('office_talent_rings nodes must align with items.')
    return errors
