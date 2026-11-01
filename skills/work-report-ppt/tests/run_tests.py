"""Minimal regression suite for the v1.4 plan/approval/render contracts.

Run from the skill directory: python -X utf8 tests/run_tests.py
No PowerPoint required here; native rendering is checked separately.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import analyze  # noqa: E402
import approval_gate  # noqa: E402
import audit  # noqa: E402
import generate  # noqa: E402
import plan_gate  # noqa: E402
import report_logic  # noqa: E402
from review_outline import render_text
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=Path.cwd()/'validation/work-report-tests')
ARGS = parser.parse_args()
ARGS.output.mkdir(parents=True, exist_ok=True)
TMPROOT = ARGS.output/'.tmp'
TMPROOT.mkdir(exist_ok=True)

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
PASSED = []
FAILED = []


def check(name, condition, detail=''):
    if condition:
        PASSED.append(name)
        print(f'PASS  {name}')
    else:
        FAILED.append((name, detail))
        print(f'FAIL  {name}  {detail}')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def design_block():
    fields = ('purpose', 'audience', 'duration_or_pages', 'key_message', 'source_scope', 'content_constraints', 'design_constraints')
    return {
        'requirements': {
            'status': 'clarified', 'open_questions': [], 'conflicts': [], 'resolved_questions': [],
            'brief': {key: '测试夹具：验证 v1.4 计划与渲染契约。' for key in fields},
            'evidence': {key: '测试夹具说明明示：只做回归验证。' for key in fields},
        },
        'selection': {'scenario': 'business', 'palette': 'P1', 'template': 'T01', 'assets': []},
        'approval': {'mode': 'confirmed', 'evidence': '测试夹具明示：按测试目的生成。', 'fields': ['scenario', 'palette', 'template', 'assets']},
    }


def make_plan(analysis_path):
    evidence = [
        {'id': 'e_gap', 'type': 'analysis', 'fact_id': 'bridge.op_profit_target.gap'},
        {'id': 'e_rev', 'type': 'analysis', 'fact_id': 'revenue.current'},
        {'id': 'e_closure', 'type': 'analysis', 'fact_id': 'bridge.op_profit_target.closure'},
    ]
    findings = [
        {'id': 'F1', 'kind': 'observation', 'text': '营业利润160万元，低于预算216万元，缺口56万元。',
         'scope': '测试事业部 2026-10', 'comparisons': ['target'], 'evidence_ids': ['e_gap']},
        {'id': 'F2', 'kind': 'observation', 'text': '营业收入1000万元。',
         'scope': '测试事业部 2026-10', 'comparisons': ['level'], 'evidence_ids': ['e_rev']},
    ]
    claims = [
        {'id': 'C1', 'text': '营业利润160万元，低于预算216万元，缺口56万元。',
         'finding_ids': ['F1'], 'comparisons': ['target'], 'scope': '测试事业部 2026-10',
         'strength': 'descriptive'},
        {'id': 'C2', 'text': '营业收入1000万元。',
         'finding_ids': ['F2'], 'comparisons': ['level'], 'scope': '测试事业部 2026-10',
         'strength': 'descriptive'},
        {'id': 'C3', 'text': '缺口可以按收入规模、贡献率和固定费用三项桥接',
         'finding_ids': ['F1'], 'comparisons': ['target'], 'scope': '测试事业部 2026-10',
         'strength': 'descriptive', 'exclusions': ['其他未列因素'],
         'method_evidence_ids': ['e_closure'], 'method': 'bridge'},
    ]
    slides = [
        {'layout': 'office_cover', 'title': '测试封面', 'purpose': '验证封面投影', 'layout_reason': '单页最小验证',
         'message_claim_id': 'C1', 'headline_claim_id': 'C1', 'finding_ids': ['F1'],
         'data': {
             'items': [{'title': '事实', 'body': '目标差距'}, {'title': '证据', 'body': '可重算'},
                       {'title': '边界', 'body': '仅测试'}, {'title': '动作', 'body': '无'}],
             'steps': ['目标', '实际', '差距', '结论'], 'metrics': [{'title': '—', 'value': '—'}] * 3,
             'rows': [], 'headers': [], 'chart': {'categories': ['—'], 'series': [{'name': '—', 'values': [0]}]},
             'subtitle': 'v1.4 回归夹具', 'meta': '仅用于自动化测试'}},
        {'layout': 'statement', 'title': '测试结论', 'purpose': '验证结论投影', 'layout_reason': '单句结论',
         'message_claim_id': 'C2', 'headline_claim_id': 'C1', 'body_finding_ids': ['F1', 'F2'],
         'finding_ids': ['F1', 'F2']},
        {'layout': 'table', 'title': '测试表格', 'purpose': '验证表格字号与页脚', 'layout_reason': '最小表格',
         'message_claim_id': 'C3', 'finding_ids': ['F1'],
         'columns': ['项目', '数值'], 'rows': [['收入', '1000'], ['营业利润', '160']], 'note': '测试夹具'},
    ]
    skipped = {'slides': [], 'skip_reason': '测试夹具不涉及', 'evidence_ids': ['e_rev']}
    return {
        'title': 'v1.4 回归测试', 'tag': '测试 · 非真实数据', 'font': 'Microsoft YaHei', 'demo': True,
        'design': design_block(),
        'narrative': {
            'decision_goal': '验证计划、批准与渲染契约。', 'audience_question': '门禁是否真的生效？',
            'key_claim_id': 'C1', 'claims': claims, 'findings': findings,
            'evidence': evidence, 'actions': [], 'requests': [],
            'actions_none_reason': '测试夹具不涉及行动。', 'requests_none_reason': '测试夹具不涉及决策请求。',
            'analysis': {'file': str(Path(analysis_path).resolve()), 'sha256': digest(analysis_path)},
            'coverage': {'goal': {'slides': [1]}, 'results': {'slides': [2]}, 'gap': {'slides': [2]},
                         'reasons': {'slides': [3]}, 'actions': skipped, 'requests': skipped},
        },
        'slides': slides,
    }


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def run_analyze(tmp, contract):
    out = Path(tmp) / 'analysis.json'
    result = analyze.analyze(contract)
    write_json(out, result)
    return out, result


def test_plan_gate():
    slide = {'layout': 'statement', 'title': 'x', 'purpose': 'x', 'layout_reason': 'x', 'message': '旧字段'}
    errors = plan_gate.validate([slide])
    check('plan_gate rejects a legacy message without a claim', any('message_claim_id' in error for error in errors), str(errors))
    slide['message_claim_id'] = 'C1'
    errors = plan_gate.validate([slide])
    check('plan_gate rejects a second copy of the page message', any('remove message' in error for error in errors), str(errors))
    slide.pop('message')
    check('plan_gate accepts message_claim_id alone', not plan_gate.validate([slide]))


def test_claim_basis(plan, base):
    broken = copy.deepcopy(plan)
    broken['narrative']['claims'][0]['comparisons'] = ['level']
    _, errors, _ = report_logic.prepare(broken, base)
    check('claim rejects target wording on a level basis', any('target basis' in error for error in errors), str(errors))


def test_exclusion(plan, base):
    broken = copy.deepcopy(plan)
    claim = broken['narrative']['claims'][0]
    claim['text'] = '缺口来自结构，不是总量'
    claim['exclusions'] = ['总量']
    claim['method_evidence_ids'] = []
    _, errors, _ = report_logic.prepare(broken, base)
    check('exclusionary claim requires a bridge', any('exclusionary' in error for error in errors), str(errors))


def test_action_conditions(plan, base):
    broken = copy.deepcopy(plan)
    broken['narrative']['actions'] = [{
        'id': 'A1', 'text': '设置接单下限', 'finding_ids': ['F1'], 'owner': '制造负责人（建议）',
        'due': '2026-11-14', 'success_criteria': '亏损收窄', 'status': 'proposed',
    }]
    broken['slides'][2]['action_ids'] = ['A1']
    _, errors, _ = report_logic.prepare(broken, base)
    check('action requires preconditions/falsifier/side effects',
          any('preconditions' in error for error in errors) and any('falsifier' in error for error in errors), str(errors))


def test_derived_explanation(plan, base):
    broken = copy.deepcopy(plan)
    source = Path(base) / 'derived.md'
    source.write_text('这是模型自行整理的说明。\n', encoding='utf-8')
    broken['narrative']['evidence'].append({
        'id': 'e_derived', 'type': 'source', 'origin': 'derived', 'purpose': 'content',
        'file': 'derived.md', 'sha256': digest(source), 'lines': [1, 1], 'quote': '模型自行整理',
    })
    broken['narrative']['findings'][0]['kind'] = 'explanation'
    broken['narrative']['findings'][0]['support_notes'] = '测试说明'
    broken['narrative']['findings'][0]['limits'] = '测试边界'
    broken['narrative']['findings'][0]['evidence_ids'] = ['e_derived']
    broken['narrative']['claims'][0]['strength'] = 'interpretive'
    _, errors, _ = report_logic.prepare(broken, base)
    check('derived source cannot alone support an explanation',
          any('primary source evidence' in error for error in errors), str(errors))


def test_projection(plan, base):
    extended = copy.deepcopy(plan)
    extended['narrative']['actions'] = [{
        'id': 'A1', 'text': '先核订单级贡献再决定是否设接单下限', 'finding_ids': ['F1'],
        'owner': '制造负责人（建议）', 'due': '2026-11-14', 'success_criteria': '提交订单级贡献与可避免成本',
        'status': 'proposed', 'preconditions': ['取得订单级边际贡献与可避免成本'],
        'falsifier': '若拒单后产品线利润未改善，则本建议不成立',
        'side_effects': ['可能失去部分订单与产能利用率'],
    }]
    extended['narrative']['requests'] = [{
        'id': 'R1', 'text': '请会议决定结构件是否设接单下限', 'finding_ids': ['F1'],
        'status': 'proposed', 'decision_question': '在订单级证据补齐前，是否维持现行接单规则？',
        'options': [
            {'text': '维持现行规则', 'condition': '订单级证据未补齐', 'consequence': '亏损可能延续但不误伤正贡献订单'},
            {'text': '设临时下限', 'condition': '确认存在负贡献订单', 'consequence': '需同步评估产能与交付影响'},
        ],
        'evidence_needed': ['订单级边际贡献', '可避免成本', '替代订单'],
    }]
    extended['slides'].extend([
        {'layout': 'office_actions', 'title': '行动', 'purpose': '验证行动投影', 'layout_reason': '单一行动记录',
         'message_claim_id': 'C1', 'action_ids': ['A1'], 'finding_ids': ['F1'],
         'data': {'items': [], 'steps': [], 'metrics': [], 'rows': [], 'headers': [], 'chart': {}}},
        {'layout': 'office_review', 'title': '请求', 'purpose': '验证请求投影', 'layout_reason': '单一请求记录',
         'message_claim_id': 'C1', 'request_ids': ['R1'], 'finding_ids': ['F1'],
         'data': {'items': [], 'steps': [], 'metrics': [], 'rows': [], 'headers': [], 'chart': {}}},
    ])
    extended['narrative']['coverage']['actions'] = {'slides': [4]}
    extended['narrative']['coverage']['requests'] = {'slides': [5]}
    bound, errors, _ = report_logic.prepare(extended, base)
    check('office_actions is projected from the action record', not errors and bound['slides'][3]['data']['rows'][0][2] == '2026-11-14', str(errors))
    check('office_review is projected from the request record',
          not errors and '维持现行规则' in bound['slides'][4]['data']['items'][0]['body'], str(errors))


def test_closing_and_record_tables(plan, base):
    request = {
        'id': 'R1', 'text': '请确认是否维持现行接单规则', 'finding_ids': ['F1'],
        'status': 'proposed', 'decision_question': '在订单级证据补齐前，是否维持现行接单规则？',
        'options': [
            {'text': '维持现行规则', 'condition': '订单级证据未补齐', 'consequence': '亏损可能延续但不误伤正贡献订单'},
            {'text': '设临时下限', 'condition': '确认存在负贡献订单', 'consequence': '需同步评估产能与交付影响'},
        ],
        'evidence_needed': ['订单级边际贡献', '可避免成本'],
    }
    extended = copy.deepcopy(plan)
    extended['narrative']['requests'] = [request]
    extended['narrative']['coverage']['requests'] = {'slides': [4]}
    closing = {'layout': 'closing', 'title': '收尾', 'purpose': '验证收尾投影',
               'layout_reason': '单一请求收束', 'message_claim_id': 'C1', 'request_ids': ['R1']}
    extended['slides'].append(closing)
    _, errors, _ = report_logic.prepare(extended, base)
    check('closing requires a headline claim', any('closing headline_claim_id' in error for error in errors), str(errors))
    closing['headline_claim_id'] = 'C1'
    bound, errors, _ = report_logic.prepare(extended, base)
    body = bound['slides'][3].get('body', '') if not errors else ''
    check('closing body is projected from the request record',
          not errors and '维持现行接单规则' in body and '待确认' in body and 'proposed' not in body,
          str(errors) + ' | ' + body)

    action = {
        'id': 'A1', 'text': '先核订单级贡献再决定是否设接单下限', 'finding_ids': ['F1'],
        'owner': '制造负责人（建议）', 'due': '2026-11-14', 'success_criteria': '提交订单级贡献与可避免成本',
        'status': 'proposed', 'preconditions': ['取得订单级边际贡献'],
        'falsifier': '若拒单后产品线利润未改善，则本建议不成立',
        'side_effects': ['可能失去部分订单'],
    }
    broken = copy.deepcopy(plan)
    broken['narrative']['actions'] = [action]
    broken['slides'][2]['action_ids'] = ['A1']
    _, errors, _ = report_logic.prepare(broken, base)
    check('a plain table cannot restate action records', any('office_actions' in error for error in errors), str(errors))


def test_image_headline(plan, base):
    extended = copy.deepcopy(plan)
    extended['narrative']['coverage']['reasons'] = {'slides': [3]}
    extended['slides'].append({'layout': 'image', 'title': '配图', 'purpose': '验证侧栏结论',
                               'layout_reason': '单图配结论', 'message_claim_id': 'C1',
                               'image': 'missing.png', 'finding_ids': ['F1']})
    _, errors, _ = report_logic.prepare(extended, base)
    check('image side commentary requires a headline claim',
          any('image headline_claim_id' in error for error in errors), str(errors))


def test_bridge_non_closure():
    contract = json.loads((ROOT / 'tests/fixtures/bridge-contract.json').read_text(encoding='utf-8-sig'))
    contract = copy.deepcopy(contract)
    contract['bridges'][0]['components'] = contract['bridges'][0]['components'][:1]
    result = analyze.analyze(ROOT / 'tests/fixtures/bridge-contract.json') if False else None
    # analyze() takes a path, so write the mutated contract beside the fixture data.
    with tempfile.TemporaryDirectory(dir=TMPROOT) as tmp:
        target = Path(tmp) / 'contract.json'
        (Path(tmp) / 'bridge-data.csv').write_bytes((ROOT / 'tests/fixtures/bridge-data.csv').read_bytes())
        write_json(target, contract)
        result = analyze.analyze(target)
    check('non-closing bridge is rejected',
          result['status'] == 'needs_clarification' and any('does not close' in issue for issue in result['issues']), str(result['issues']))


def test_font_and_disclosure(plan_path, output_path):
    with zipfile.ZipFile(output_path) as archive:
        slides = [name for name in archive.namelist() if name.startswith('ppt/slides/slide') and name.endswith('.xml')]
        missing_ea = []
        missing_disclosure = []
        for name in slides:
            root = ET.fromstring(archive.read(name))
            text = ''.join(node.text or '' for node in root.findall('.//a:t', NS))
            if '合成模板' not in text:
                missing_disclosure.append(name)
            for props in root.findall('.//a:rPr', NS) + root.findall('.//a:defRPr', NS):
                latin = props.find('a:latin', NS)
                if latin is None or latin.get('typeface', '').startswith('+'):
                    continue
                ea = props.find('a:ea', NS)
                if ea is None or ea.get('typeface') != 'Microsoft YaHei':
                    missing_ea.append((name, None if ea is None else ea.get('typeface')))
                    break
    check('every declared font also sets the East Asian slot', not missing_ea, str(missing_ea[:3]))
    check('disclosure appears on every slide', not missing_disclosure, str(missing_disclosure))
    report = audit.audit(output_path, 'Microsoft YaHei', '合成模板')
    check('audit reports complete font and disclosure contracts',
          report['font_contract_ok'] and report['disclosure_complete'], json.dumps(report['font_contract'][:2], ensure_ascii=False))


def main():
    test_plan_gate()
    test_bridge_non_closure()
    with tempfile.TemporaryDirectory(dir=TMPROOT) as tmp:
        tmp = Path(tmp)
        contract = ROOT / 'tests/fixtures/bridge-contract.json'
        analysis, result = run_analyze(tmp, contract)
        check('bridge fixture analyzes ready', result['status'] == 'ready', str(result['issues']))
        plan = make_plan(analysis)
        base = tmp
        test_claim_basis(plan, base)
        test_exclusion(plan, base)
        test_action_conditions(plan, base)
        test_derived_explanation(plan, base)
        test_projection(plan, base)
        test_closing_and_record_tables(plan, base)
        test_image_headline(plan, base)

        plan_path = tmp / 'prepared-plan.json'
        outline_path = tmp / 'outline.md'
        write_json(plan_path, plan)
        outline_path.write_text('# 无关提纲\n', encoding='utf-8')
        check('unrelated outline is rejected', bool(approval_gate.reviewed_content_errors(plan_path, outline_path)))
        bound, errors, audit_report = report_logic.prepare(plan, base)
        outline_path.write_text(render_text(bound, audit_report), encoding='utf-8')
        approved = subprocess.run([sys.executable, str(SCRIPTS / 'approve_plan.py'), '--plan', str(plan_path),
                                   '--outline', str(outline_path), '--mode', 'confirmed',
                                   '--quote', '同意按此计划制作', '--confirm'], capture_output=True, text=True)
        check('approval recorder writes a sidecar', approved.returncode == 0, approved.stderr)
        sidecar = approval_gate.approval_path_for(plan_path)
        check('approval validates the exact plan', not approval_gate.validate(plan_path, sidecar))
        plan_path.write_text(plan_path.read_text(encoding='utf-8') + '\n', encoding='utf-8')
        check('edited plan invalidates approval', bool(approval_gate.validate(plan_path, sidecar)))
        write_json(plan_path, plan)

        output = tmp / 'report.pptx'
        built = generate.build(plan, output, tmp, plan_path=plan_path)
        check('generation succeeds with approval', output.exists() and built['slides'] == 3, str(built))
        test_font_and_disclosure(plan_path, output)
        changed = copy.deepcopy(plan)
        changed['title'] = '未经审阅的改动'
        try:
            generate.build(changed,tmp/'changed.pptx',tmp,plan_path=plan_path)
            refused = False
        except ValueError as error:
            refused = 'differs from the approved' in str(error)
        check('API cannot render a different document against approved file', refused)

    print(f'\n{len(PASSED)} passed, {len(FAILED)} failed')
    for name, detail in FAILED:
        print(f'  - {name}: {detail}')
    write_json(ARGS.output/'tests.json', {'passed':len(PASSED),'failed':FAILED,'checks':PASSED})
    TMPROOT.rmdir()
    return 1 if FAILED else 0


if __name__ == '__main__':
    raise SystemExit(main())
