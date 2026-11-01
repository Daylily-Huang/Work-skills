"""Validate report reasoning and project one narrative source into slide fields.

Evidence hashes prove provenance, not entailment. Typed claims additionally bind each
page message to its comparison basis, scope and strength; exclusionary attribution
requires a computed bridge rather than a change in prose alone.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date
from decimal import Decimal, localcontext, ROUND_HALF_UP
from pathlib import Path
import math
import re
import json
from analyze import Clarification, digest, verify_artifact
from design_gate import filled
from plan_gate import DECORATIVE
from layout_contract import validate_data

ROLES = {'goal', 'results', 'gap', 'reasons', 'actions', 'requests'}
# Status is an internal enum; projected pages must not leak it into user-facing copy.
STATUS_LABELS = {'proposed': '待确认', 'agreed': '已确认'}
COMPARISONS = {'target', 'previous', 'year_ago', 'ytd_target', 'ytd_year_ago', 'level'}
STRENGTHS = {'descriptive', 'interpretive', 'conditional'}
ORIGINS = {'user_supplied', 'external', 'derived', 'synthetic'}
BINDABLE = re.compile(r'(?:(?:chart|data\.(?:chart|comparison_chart|ranking_chart|allocation_chart|donut|segment_chart))\.series\.\d+\.values(?:\.\d+)?|(?:items|data\.metrics|data\.side_metrics|data\.waterfall|data\.funnel)\.\d+\.value|data\.score_progress\.\d+)\Z')

def _quant_paths(slide, black_cover):
    """Known rendered chart/KPI fields; prose, tables, and dates need source review."""
    layout = slide.get('layout', '')
    data = slide.get('data', {})
    if not isinstance(data, dict): data = {}
    charts = []
    metrics = []
    if layout in ('bar', 'line'):
        charts.append(('chart', slide.get('chart', {})))
    if layout == 'metrics':
        metrics.extend(f'items.{index}.value' for index, _ in enumerate(slide.get('items', [])))
    office = layout.removeprefix('office_') if layout.startswith('office_') else ''
    fields = {'summary':['chart'], 'growth':['chart'], 'resource':['allocation_chart'], 'delivery':['donut'],
              'customer':['segment_chart'], 'retention':['donut'], 'training':['donut'],
              'sales':['comparison_chart','ranking_chart'], 'finance':['allocation_chart'], 'channel':['ranking_chart']}
    for field in fields.get(office, []):
        charts.append(('data.' + field, data.get(field, {})))
    count = {'summary':None,'scorecard':4,'delivery':3,'growth':3,'retention':2,'training':2,'sales':None,'finance':3}
    if office == 'cover' and black_cover: count['cover'] = 3
    if office in count:
        values = data.get('metrics', [])
        if count[office] is not None: values = values[:count[office]]
        metrics.extend(f'data.metrics.{index}.value' for index, _ in enumerate(values))
    if office == 'growth': metrics.extend(f'data.side_metrics.{index}.value' for index, _ in enumerate(data.get('side_metrics', [])))
    if office in ('finance', 'funnel'):
        field = 'waterfall' if office == 'finance' else 'funnel'
        metrics.extend(f'data.{field}.{index}.value' for index, _ in enumerate(data.get(field, [])))
    if office == 'scorecard': metrics.extend(f'data.score_progress.{index}' for index, _ in enumerate(data.get('score_progress', [])))
    return charts, metrics

def _index(items, label, errors):
    if not isinstance(items, list):
        errors.append(f'narrative.{label} must be an explicit list.')
        return {}
    found = {}
    for item in items:
        if not isinstance(item, dict) or not filled(item.get('id')) or item['id'] in found:
            errors.append(f'{label}: records need unique, nonempty IDs.')
        else:
            found[item['id']] = item
    return found

def _refs(value, known, label, errors, required=False):
    if not isinstance(value, list) or not all(filled(item) for item in value) or len(set(value)) != len(value):
        errors.append(f'{label}: declare a list of unique reference IDs.')
        return []
    if set(value) - set(known) or (required and not value):
        errors.append(f'{label}: missing or unknown reference IDs.')
    return [item for item in value if item in known]

def _formatted(fact, binding):
    if fact.get('value') is None or fact.get('status') != 'computed':
        raise Clarification('Undefined analysis values cannot become chart numbers or display metrics.')
    value = Decimal(fact['value'])
    kind = binding.get('format')
    if kind == 'number':
        result = float(value)
        if not math.isfinite(result):
            raise Clarification('A bound chart value is outside the finite rendering range.')
        return result
    decimals = binding.get('decimals')
    if not isinstance(decimals, int) or isinstance(decimals, bool) or not 0 <= decimals <= 6:
        raise Clarification('Display bindings require decimals: 0–6; analysis retains the unrounded value.')
    with localcontext() as context:
        context.prec = 160
        context.rounding = ROUND_HALF_UP
        if kind == 'percent':
            if fact['unit'] != 'ratio': raise Clarification('Only a ratio fact can use percent formatting.')
            return f'{value * 100:.{decimals}f}%'
        if kind == 'pp':
            if fact['unit'] != 'pp': raise Clarification('Percentage-point display requires a pp fact, not a percent or amount.')
            return f'{value:.{decimals}f}个百分点'
        if kind == 'text':
            body = f'{value:,.{decimals}f}' if binding.get('group') is True else f'{value:.{decimals}f}'
            return body + (fact['unit'] if binding.get('append_unit') is True else '')
    raise Clarification('Binding format must be number, text, percent, or pp.')

def _destination(slide, path):
    if not isinstance(path, str) or not BINDABLE.fullmatch(path):
        raise Clarification('Binding target must be a supported chart-values or metric-value field.')
    parts = path.split('.')
    target = slide
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    key = int(parts[-1]) if isinstance(target, list) else parts[-1]
    old = target[key]
    return target, key, old

def _string_list(value):
    return isinstance(value, list) and bool(value) and all(filled(item) for item in value)


def _validate_claims(narrative, findings, evidence, errors):
    claims = _index(narrative.get('claims'), 'claims', errors)
    if not claims:
        errors.append('Declare narrative.claims; page messages must reference a typed claim, not an independent prose summary.')
    for identity, claim in claims.items():
        references = _refs(claim.get('finding_ids'), findings, f'Claim {identity} findings', errors, True)
        if not filled(claim.get('text')) or not filled(claim.get('scope')):
            errors.append(f'Claim {identity}: declare the exact display text and its business/period scope.')
        comparisons = claim.get('comparisons')
        if not isinstance(comparisons, list) or not comparisons or len(set(comparisons)) != len(comparisons) or set(comparisons) - COMPARISONS:
            errors.append(f'Claim {identity}: comparisons must use target/previous/year_ago/ytd_target/ytd_year_ago/level.')
            comparisons = []
        supported = {basis for ref in references for basis in findings[ref].get('comparisons', [])}
        if set(comparisons) - supported:
            errors.append(f'Claim {identity}: comparison basis is not present in the referenced findings; do not mix target and change-basis conclusions.')
        strength = claim.get('strength')
        kinds = {findings[ref].get('kind') for ref in references}
        if strength not in STRENGTHS:
            errors.append(f'Claim {identity}: strength must be descriptive/interpretive/conditional.')
        elif strength == 'descriptive' and kinds - {'observation'}:
            errors.append(f'Claim {identity}: descriptive claims may cite observations only.')
        elif strength == 'interpretive' and 'explanation' not in kinds:
            errors.append(f'Claim {identity}: an interpretive claim needs a sourced explanation with explicit limits.')
        elif strength == 'conditional' and (not _string_list(claim.get('conditions')) or not filled(claim.get('falsifier'))):
            errors.append(f'Claim {identity}: conditional claims need conditions and a falsifier; never promise an untested outcome.')
        text = claim.get('text', '')
        required_bases = []
        if any(word in text for word in ('预算', '目标', '缺口')): required_bases.append(('target basis', {'target', 'ytd_target'}))
        if '环比' in text: required_bases.append(('previous basis', {'previous'}))
        if '同比' in text: required_bases.append(('year-ago basis', {'year_ago', 'ytd_year_ago'}))
        for label, accepted in required_bases:
            if not accepted.intersection(comparisons):
                errors.append(f'Claim {identity}: display text requires {label}; the cited comparison does not support it.')
        exclusions = claim.get('exclusions', [])
        if exclusions is None: exclusions = []
        method_refs = claim.get('method_evidence_ids', [])
        if exclusions:
            _refs(method_refs, evidence, f'Claim {identity} method evidence', errors, True)
            if not any(evidence.get(ref, {}).get('type') == 'analysis' and (evidence[ref].get('fact_id', '').startswith('bridge.') or '.bridge.' in evidence[ref].get('fact_id', '')) for ref in method_refs):
                errors.append(f'Claim {identity}: exclusionary attribution requires a computed target-gap bridge fact.')
        # A negation can state a valid boundary (e.g. "不是因果证明").
        # Exclusions are explicit metadata, not inferred by a blanket keyword ban.
    return claims


def _clause(text):
    """Join clauses without doubling the sentence punctuation."""
    return text.rstrip('。；')


def _sentence(text):
    return text if text.endswith(('。', '？', '！', '；')) else text + '。'


def _finding_text(identity, findings):
    item = findings[identity]
    text = item.get('text', '')
    if item.get('kind') == 'hypothesis':
        text = '待核实：' + text
    # text must retain any business qualification needed to understand the claim.
    # Full validation procedures and limits remain in the outline and slide notes.
    return _sentence(text)


def _project_actions(slide, action_ids, actions):
    selected = [item for item in actions.values() if item['id'] in action_ids]
    required = ('text', 'owner', 'due', 'success_criteria', 'falsifier', 'status')
    if any(not all(filled(item.get(field)) for field in required) or not _string_list(item.get('preconditions')) or not _string_list(item.get('side_effects')) or item.get('status') not in STATUS_LABELS for item in selected):
        return
    data = slide.setdefault('data', {})
    for field in ('items', 'steps'):
        data.pop(field, None)
    data['headers'] = ['行动／状态', '负责人', '期限', '交付结果', '依赖与影响']
    data['rows'] = [[item['text']+'（'+STATUS_LABELS[item['status']]+'）', item['owner'], item['due'], item['success_criteria'],
                     '、'.join(item['preconditions']) + '；' + '、'.join(item['side_effects'])] for item in selected]


def _project_requests(slide, request_ids, requests):
    selected = [item for item in requests.values() if item['id'] in request_ids]
    if any(not filled(item.get('text')) or not filled(item.get('decision_question')) or not isinstance(item.get('options'), list) or not _string_list(item.get('evidence_needed')) or item.get('status') not in STATUS_LABELS for item in selected):
        return
    if any(any(not isinstance(option, dict) or not all(filled(option.get(field)) for field in ('text', 'condition', 'consequence')) for option in item['options']) for item in selected):
        return
    data = slide.setdefault('data', {})
    data['items'] = []
    for item in selected[:3]:
        options = '\n'.join(f"{opt['text']}：{opt['condition']}；{opt['consequence']}" for opt in item['options'])
        data['items'].append({'title': item['text']+'（'+STATUS_LABELS[item['status']]+'）',
                              'body': _sentence(item['decision_question']) + '\n' + options +
                              '\n需补齐：' + '、'.join(item['evidence_needed'])})
    for field in ('steps', 'headline', 'footer_message'):
        data.pop(field, None)


def prepare(doc, base):
    """Return a detached bound plan, structural errors, and an evidence/binding audit."""
    result = deepcopy(doc)
    base = Path(base)
    errors = []
    metadata = {'bindings': [], 'slide_notes': {}, 'slide_labels': {}, 'semantic_review': 'required'}
    narrative = result.get('narrative')
    if not isinstance(narrative, dict):
        return result, ['A narrative plan is required: decision goal, audience question, evidence, findings, actions, and role coverage.'], metadata
    for field in ('decision_goal', 'audience_question', 'key_claim_id'):
        if not filled(narrative.get(field)):
            errors.append(f'narrative.{field} must express the report purpose or reference the key typed claim.')
    evidence = _index(narrative.get('evidence'), 'evidence', errors)
    findings = _index(narrative.get('findings'), 'findings', errors)
    actions = _index(narrative.get('actions'), 'actions', errors)
    requests = _index(narrative.get('requests'), 'requests', errors)
    claims = _validate_claims(narrative, findings, evidence, errors)
    if narrative.get('key_claim_id') not in claims:
        errors.append('narrative.key_claim_id must reference a declared claim; key_takeaway is projected from it.')
    else:
        narrative['key_takeaway'] = claims[narrative['key_claim_id']]['text']
    if not findings:
        errors.append('Plan at least one supported finding; a pile of source materials is not a report conclusion.')
    facts = {}
    analysis = narrative.get('analysis')
    if analysis is not None:
        try:
            if not isinstance(analysis, dict) or not filled(analysis.get('file')) or not filled(analysis.get('sha256')):
                raise Clarification('Declare the actual analysis file and SHA256.')
            artifact = verify_artifact(base / analysis['file'], analysis['sha256'])
            facts = {item['id']: item for item in artifact['facts']}
            metadata['analysis'] = {'file': str((base / analysis['file']).resolve()), 'sha256': analysis['sha256'], 'source': artifact['source'], 'contract': artifact['contract']}
        except (Clarification, KeyError, TypeError, ValueError, OSError) as error:
            errors.append('Analysis binding: ' + str(error))
    for identity, item in evidence.items():
        try:
            if item.get('type') == 'analysis':
                if item.get('fact_id') not in facts:
                    raise Clarification('Unknown fact ID or missing verified analysis artifact.')
            elif item.get('type') == 'source':
                if item.get('origin') not in ORIGINS or item.get('purpose') not in ('content', 'approval', 'clarification'):
                    raise Clarification('Source evidence must declare origin=user_supplied/external/derived/synthetic and purpose=content/approval/clarification.')
                if not filled(item.get('file')) or not filled(item.get('sha256')) or not filled(item.get('quote')):
                    raise Clarification('Source evidence requires a real file, SHA256, and exact quote.')
                path = base / item['file']
                if digest(path) != item['sha256']:
                    raise Clarification('Source evidence file hash does not match.')
                lines = item.get('lines')
                content = path.read_text(encoding='utf-8-sig').splitlines()
                if not isinstance(lines, list) or len(lines) != 2 or any(not isinstance(value, int) or isinstance(value, bool) for value in lines) or not 1 <= lines[0] <= lines[1] <= len(content):
                    raise Clarification('Source evidence needs valid inclusive one-based line bounds.')
                if item['quote'] not in '\n'.join(content[lines[0] - 1:lines[1]]):
                    raise Clarification('The quote does not occur at the declared source lines.')
            else:
                raise Clarification('Evidence type must be source or analysis.')
        except (Clarification, KeyError, TypeError, ValueError, OSError, UnicodeError) as error:
            errors.append(f'Evidence {identity}: {error}')
    for identity, item in findings.items():
        if not filled(item.get('text')) or item.get('kind') not in ('observation', 'hypothesis', 'explanation'):
            errors.append(f'Finding {identity}: declare text and observation/hypothesis/explanation.')
        comparisons = item.get('comparisons')
        if not isinstance(comparisons, list) or not comparisons or len(set(comparisons)) != len(comparisons) or set(comparisons) - COMPARISONS or not filled(item.get('scope')):
            errors.append(f'Finding {identity}: declare its scope and explicit comparison basis; level is for a level-only observation.')
        references = _refs(item.get('evidence_ids'), evidence, f'Finding {identity}', errors, True)
        numeric = [evidence[ref].get('fact_id', '') for ref in references if evidence[ref].get('type') == 'analysis']
        if numeric and not any(evidence[ref].get('type') == 'source' and evidence[ref].get('purpose') == 'content' for ref in references):
            supported = set()
            target_fields = {'target', 'target_gap', 'actual_to_target', 'required_improvement', 'target_gap_percentage_points', 'required_improvement_percentage_points'}
            for fact_id in numeric:
                parts = fact_id.split('.')
                if parts[0] == 'bridge' or (len(parts)>1 and parts[1] in target_fields): supported.add('target')
                if len(parts)>1 and parts[1] in ('previous','year_ago'): supported.add(parts[1])
            declared = {'target' if x=='ytd_target' else 'year_ago' if x=='ytd_year_ago' else x for x in comparisons or []}
            if declared - {'level'} - supported:
                errors.append(f'Finding {identity}: comparison basis is not supported by its numeric evidence; a previous-period fact cannot stand in for a target gap.')
        if item.get('kind') == 'hypothesis' and not filled(item.get('validation')):
            errors.append(f'Finding {identity}: a hypothesis needs a concrete validation step and must remain labeled unverified.')
        if item.get('kind') == 'explanation':
            supporting = [evidence.get(reference, {}) for reference in references]
            primary = [entry for entry in supporting if entry.get('type') == 'source' and entry.get('origin') in ('user_supplied', 'external')]
            simulated = result.get('demo') is True and any(entry.get('type') == 'source' and entry.get('origin') == 'synthetic' for entry in supporting)
            if (not primary and not simulated) or not all(filled(item.get(field)) for field in ('support_notes', 'limits')):
                errors.append(f'Finding {identity}: explanations need primary source evidence, support notes and limits; derived/self-written sources cannot circle-support causality outside an explicit demo.')
    for identity, item in actions.items():
        _refs(item.get('finding_ids'), findings, f'Action {identity}', errors, True)
        if not all(filled(item.get(field)) for field in ('text', 'owner', 'due', 'success_criteria', 'falsifier')) or item.get('status') not in ('proposed', 'agreed'):
            errors.append(f'Action {identity}: specify action, owner, ISO due date, success criterion, falsifier, and proposed/agreed status.')
        if not _string_list(item.get('preconditions')) or not _string_list(item.get('side_effects')):
            errors.append(f'Action {identity}: declare preconditions and possible side effects; responsibility fields do not prove the action will work.')
        else:
            try:
                date.fromisoformat(item['due'])
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', item['due']): raise ValueError('ISO date required')
            except ValueError:
                errors.append(f'Action {identity}: due date is invalid.')
        if item.get('status') == 'agreed':
            agreed_refs = _refs(item.get('agreement_evidence_ids'), evidence, f'Agreed action {identity}', errors, True)
            if not any(evidence.get(reference, {}).get('type') == 'source' and evidence[reference].get('origin') == 'user_supplied' and evidence[reference].get('purpose') == 'approval' for reference in agreed_refs):
                errors.append(f'Agreed action {identity}: agreement needs user_supplied evidence whose purpose is approval; generic source quotes and numeric facts do not prove consent.')
    for identity, item in requests.items():
        _refs(item.get('finding_ids'), findings, f'Request {identity}', errors, True)
        if not all(filled(item.get(field)) for field in ('text', 'decision_question')) or item.get('status') not in ('proposed', 'agreed'):
            errors.append(f'Request {identity}: declare the decision/resource request, exact decision question and proposed/agreed status.')
        options = item.get('options')
        if not isinstance(options, list) or len(options) < 2 or any(not isinstance(option, dict) or not all(filled(option.get(field)) for field in ('text', 'condition', 'consequence')) for option in options):
            errors.append(f'Request {identity}: provide at least two options, each with condition and consequence; do not hard-code an unverified result.')
        if not _string_list(item.get('evidence_needed')):
            errors.append(f'Request {identity}: declare evidence still needed before decision.')
        if item.get('status') == 'agreed':
            agreed_refs = _refs(item.get('agreement_evidence_ids'), evidence, f'Agreed request {identity}', errors, True)
            if not any(evidence.get(reference, {}).get('type') == 'source' and evidence[reference].get('origin') == 'user_supplied' and evidence[reference].get('purpose') == 'approval' for reference in agreed_refs):
                errors.append(f'Agreed request {identity}: agreement needs user_supplied approval evidence, not a generic quote or numeric fact.')
    for name, items in (('actions', actions), ('requests', requests)):
        if not items and not filled(narrative.get(name + '_none_reason')):
            errors.append(f'Explain an explicitly omitted {name} section; do not silently discard it.')
    slides = result.get('slides', [])
    if not isinstance(slides, list):
        return result, errors + ['slides must be a list.'], metadata
    coverage = narrative.get('coverage')
    covered = set()
    if not isinstance(coverage, dict) or set(coverage) != ROLES:
        errors.append('Cover goal/results/gap/reasons/actions/requests, or explicitly justify an omitted role with source evidence; roles may share pages.')
    else:
        for role, entry in coverage.items():
            if not isinstance(entry, dict):
                errors.append(f'Coverage {role} must be an object.'); continue
            pages = entry.get('slides', [])
            if not isinstance(pages, list) or any(not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= len(slides) for page in pages) or len(set(pages)) != len(pages):
                errors.append(f'Coverage {role}: invalid page references.'); continue
            if pages:
                covered.update(pages)
            else:
                if not filled(entry.get('skip_reason')):
                    errors.append(f'Coverage {role}: explain why this role is intentionally omitted.')
                _refs(entry.get('evidence_ids'), evidence, f'Coverage {role} omission', errors, True)
                if (role == 'actions' and actions) or (role == 'requests' and requests):
                    errors.append(f'Coverage {role}: cannot omit a role whose records are present.')
    used_findings, used_actions, used_requests = set(), set(), set()
    used_claims = {narrative.get('key_claim_id')}
    catalog = json.loads((Path(__file__).resolve().parents[1] / 'assets/design-catalog.json').read_text(encoding='utf-8'))
    selection = result.get('design', {}).get('selection', {})
    black_cover = any(item['id'] == selection.get('template') and item.get('style', '').startswith('black') for item in catalog['templates'])
    for index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            errors.append(f'Slide {index} must be an object.'); continue
        claim_id = slide.get('message_claim_id')
        if claim_id not in claims:
            errors.append(f'Slide {index}: message_claim_id must reference a typed narrative claim; independent page messages are not allowed.')
        else:
            # Kept out of the slide on purpose: the outline shows it, the plan must not carry a second copy.
            metadata.setdefault('slide_messages', {})[str(index)] = claims[claim_id]['text']
            used_claims.add(claim_id)
        if slide.get('layout') == 'statement':
            headline_id = slide.get('headline_claim_id')
            if headline_id not in claims:
                errors.append(f'Slide {index}: statement headline_claim_id is required; the main conclusion must come from narrative.claims.')
            else:
                slide['headline'] = claims[headline_id]['text']
                used_claims.add(headline_id)
            body_refs = _refs(slide.get('body_finding_ids'), findings, f'Slide {index} body findings', errors, True)
            slide['body'] = '\n'.join(_finding_text(ref, findings) for ref in body_refs if ref in findings)
            used_findings.update(body_refs)
        if slide.get('layout') == 'office_cover':
            headline_id = slide.get('headline_claim_id')
            if headline_id not in claims:
                errors.append(f'Slide {index}: office_cover headline_claim_id is required.')
            else:
                slide.setdefault('data', {})['headline'] = claims[headline_id]['text']
                used_claims.add(headline_id)
        if slide.get('layout') == 'image':
            headline_id = slide.get('headline_claim_id')
            if headline_id not in claims:
                errors.append(f'Slide {index}: image headline_claim_id is required; side commentary is a conclusion and must come from narrative.claims.')
            else:
                slide['headline'] = claims[headline_id]['text']
                used_claims.add(headline_id)
        if slide.get('layout') not in DECORATIVE and index not in covered:
            errors.append(f'Slide {index} has no role in the report storyline.')
        finding_refs = _refs(slide.get('finding_ids', []), findings, f'Slide {index} findings', errors)
        action_refs = _refs(slide.get('action_ids', []), actions, f'Slide {index} actions', errors)
        request_refs = _refs(slide.get('request_ids', []), requests, f'Slide {index} requests', errors)
        if slide.get('layout') == 'office_actions':
            if not action_refs: errors.append(f'Slide {index}: office_actions must reference the action records it renders.')
            else: _project_actions(slide, action_refs, actions)
        if slide.get('layout') == 'table' and (action_refs or request_refs):
            errors.append(f'Slide {index}: a plain table cannot restate owners, dates or status; use office_actions or office_review so the rows are projected from the records.')
        if slide.get('layout') == 'office_review':
            if not request_refs: errors.append(f'Slide {index}: office_review must reference the request records it renders.')
            elif len(request_refs)>3: errors.append(f'Slide {index}: office_review capacity is 3 requests; split the page, never truncate.')
            else: _project_requests(slide, request_refs, requests)
        if slide.get('layout') == 'closing':
            headline_id = slide.get('headline_claim_id')
            if headline_id not in claims:
                errors.append(f'Slide {index}: closing headline_claim_id is required; the last page asks for a decision and must not restate it in new words.')
            else:
                slide['headline'] = claims[headline_id]['text']
                used_claims.add(headline_id)
            selected = [requests[ref] for ref in request_refs if ref in requests]
            if len(selected)>2: errors.append(f'Slide {index}: closing capacity is 2 requests; use another decision page.')
            if selected:
                slide['body'] = '\n'.join(STATUS_LABELS[item['status']]+'：'+item['decision_question'] for item in selected[:2])
            else:
                slide['body'] = ''
        used_findings.update(finding_refs); used_actions.update(action_refs); used_requests.update(request_refs)
        # Labels/notes inherit all conclusions actually projected onto the page.
        for cid in (claim_id, slide.get('headline_claim_id')):
            finding_refs = list(dict.fromkeys(finding_refs + claims.get(cid, {}).get('finding_ids', [])))
        finding_refs = [ref for ref in finding_refs if ref in findings]
        used_findings.update(finding_refs)
        labels = []
        if any(findings.get(identity, {}).get('kind') == 'hypothesis' for identity in finding_refs):
            labels.append('原因待核实')
        if slide.get('layout') not in ('office_actions','office_review','closing') and (any(actions.get(identity, {}).get('status') == 'proposed' for identity in action_refs) or any(requests.get(identity, {}).get('status') == 'proposed' for identity in request_refs)):
            labels.append('待确认')
        metadata['slide_labels'][str(index)] = ' · '.join(labels)
        direct = _refs(slide.get('evidence_ids', []), evidence, f'Slide {index} evidence', errors)
        if slide.get('layout') not in DECORATIVE and not (finding_refs or action_refs or request_refs or direct):
            errors.append(f'Slide {index} needs a traceable finding, action, request, or source.')
        note_ids = set(direct)
        for identity in finding_refs:
            note_ids.update(findings.get(identity, {}).get('evidence_ids', []))
        metadata['slide_notes'][str(index)] = '\n'.join(
            f'Evidence {identity}: {evidence[identity].get("file", "analysis")} / {evidence[identity].get("fact_id", evidence[identity].get("lines"))}'
            for identity in sorted(note_ids) if identity in evidence
        )
        # Keep the complete authoring record inspectable without putting a
        # repeated explanation of our checking procedure on the slide itself.
        metadata['slide_notes'][str(index)] += '\n内容与执行记录：\n' + json.dumps({
            'findings': [findings[ref] for ref in finding_refs],
            'actions': [actions[ref] for ref in action_refs],
            'requests': [requests[ref] for ref in request_refs],
        }, ensure_ascii=False, indent=2)
        bindings = slide.get('analysis_bindings', [])
        if not isinstance(bindings, list):
            errors.append(f'Slide {index}: analysis_bindings must be a list.'); continue
        destinations = []
        for binding in bindings:
            try:
                path = binding['path']
                if any(path == old or path.startswith(old + '.') or old.startswith(path + '.') for old in destinations):
                    raise Clarification('Duplicate or overlapping binding targets are not allowed.')
                destinations.append(path)
                parent, key, old = _destination(slide, path)
                if 'fact_ids' in binding:
                    ids = binding['fact_ids']
                    if not isinstance(old, list) or not isinstance(ids, list) or not ids or binding.get('format') != 'number':
                        raise Clarification('Array bindings need fact_ids, a numeric chart-values array, and format: number.')
                    if not all(identity in facts for identity in ids): raise Clarification('Unknown fact in array binding.')
                    value = [_formatted(facts[identity], binding) for identity in ids]
                else:
                    identity = binding['fact_id']
                    if identity not in facts or isinstance(old, (dict, list)):
                        raise Clarification('A scalar binding needs a known fact and scalar destination.')
                    ids = [identity]
                    value = _formatted(facts[identity], binding)
                parent[key] = value
                metadata['bindings'].append({'slide': index, 'path': path, 'fact_ids': ids, 'value': value})
            except (Clarification, KeyError, TypeError, ValueError, IndexError) as error:
                errors.append(f'Slide {index} binding: {error}')
        charts, metric_paths = _quant_paths(slide, black_cover)
        style = next((item.get('style','') for item in catalog['templates'] if item['id']==selection.get('template')), '')
        errors.extend(f'Slide {index}: {error}' for error in validate_data(slide,style))
        if (charts or metric_paths) and not analysis:
            errors.append(f'Slide {index}: quantitative charts and KPIs require a verified analysis artifact, not manually filled template numbers.')
        for path in metric_paths:
            if path not in destinations:
                errors.append(f'Slide {index}: quantitative field {path} must bind an analysis fact.')
        for prefix, chart in charts:
            if not isinstance(chart, dict) or not isinstance(chart.get('series'), list):
                errors.append(f'Slide {index}: chart specification must contain an explicit series list.'); continue
            for position, series in enumerate(chart['series']):
                if not isinstance(series, dict) or not isinstance(series.get('values'), list):
                    errors.append(f'Slide {index}: chart series must contain an explicit values list.'); continue
                path = f'{prefix}.series.{position}.values'
                if path not in destinations and not all(f'{path}.{offset}' in destinations for offset, _ in enumerate(series.get('values', []))):
                    errors.append(f'Slide {index}: chart values {path} must bind analysis facts.')
    for name, items, used in (('findings', findings, used_findings), ('actions', actions, used_actions), ('requests', requests, used_requests), ('claims', claims, used_claims)):
        if set(items) - used:
            errors.append(f'Orphan {name} are not connected to any page: ' + ', '.join(sorted(set(items) - used)))
    return result, errors, metadata
