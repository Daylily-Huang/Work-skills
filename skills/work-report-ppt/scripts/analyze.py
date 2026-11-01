"""Auditable descriptive analysis of explicitly scoped, normalized work-report data."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import sys
from design_gate import requirements_errors, filled

class Clarification(ValueError):
    pass

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def number(value, label):
    if isinstance(value, bool) or value is None or not str(value).strip():
        raise Clarification(f'{label}: missing or nonnumeric value; ask the user, never replace with zero.')
    text = str(value).strip()
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', text):
        raise Clarification(f'{label}: use an explicitly normalized number, without percent signs, currency, or thousands separators.')
    try:
        result = Decimal(text)
    except InvalidOperation as error:
        raise Clarification(f'{label}: invalid number.') from error
    if not result.is_finite() or result.adjusted() > 100 or result.adjusted() < -100:
        raise Clarification(f'{label}: finite values within the supported decimal range are required.')
    return result

def text(value):
    return '' if value is None else str(value).strip()

def source_rows(spec, base):
    path = (base / spec['file']).resolve()
    kind = spec['format']
    if not path.is_file():
        raise Clarification(f'Input file does not exist: {path}')
    if kind == 'csv':
        encoding = spec.get('encoding')
        delimiter = spec.get('delimiter')
        if encoding not in ('utf-8', 'utf-8-sig', 'gb18030') or delimiter not in (',', '\t'):
            raise Clarification('CSV encoding and delimiter must be explicitly specified; do not guess.')
        with path.open(encoding=encoding, newline='') as stream:
            reader = csv.DictReader(stream, delimiter=delimiter)
            headers = reader.fieldnames or []
            rows = [(index, row) for index, row in enumerate(reader, 2)]
            if any(None in row for _, row in rows):
                raise Clarification('CSV contains extra unheaded fields; fix quoting/column alignment before analysis.')
    elif kind == 'json':
        data = read_json(path)
        records = data.get('rows') if isinstance(data, dict) else data
        if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
            raise Clarification('JSON input must be a list of row objects or an object containing rows.')
        headers = list(dict.fromkeys(key for row in records for key in row))
        rows = list(enumerate(records, 1))
    elif kind == 'xlsx':
        import openpyxl
        if not filled(spec.get('sheet')) or spec.get('formula_policy') != 'reject':
            raise Clarification('Specify the XLSX sheet and formula_policy: reject; cached formula freshness is not assumed.')
        book = openpyxl.load_workbook(path, read_only=True, data_only=False)
        try:
            if spec['sheet'] not in book.sheetnames:
                raise Clarification('Declared XLSX sheet does not exist.')
            iterator = iter(book[spec['sheet']].iter_rows())
            header = next(iterator, ())
            headers = [cell.value for cell in header]
            rows = []
            selected = set(spec['columns'].values())
            for line, cells in enumerate(iterator, 2):
                if all(cell.value is None for cell in cells):
                    continue
                row = {}
                for name, cell in zip(headers, cells):
                    if name in selected and cell.data_type in ('f', 'e'):
                        raise Clarification(f'XLSX row {line}: formula/error input must be resolved and exported as confirmed values first.')
                    row[name] = cell.value
                rows.append((line, row))
        finally:
            book.close()
    else:
        raise Clarification('Supported inputs: csv, json, xlsx; convert other formats explicitly.')
    if not headers or any(not isinstance(item, str) or not item.strip() for item in headers) or len(set(headers)) != len(headers):
        raise Clarification('Input headers must be nonempty and unique.')
    if not rows:
        raise Clarification('Input contains no records.')
    columns = spec.get('columns')
    if not isinstance(columns, dict) or not all(isinstance(key, str) and filled(value) for key, value in columns.items()):
        raise Clarification('Declare the canonical-to-source column mapping.')
    if set(columns.values()) - set(headers):
        raise Clarification('Declared source columns are missing; do not silently omit them.')
    if len(set(columns.values())) != len(columns):
        raise Clarification('One source column cannot silently serve two declared fields.')
    return path, [(line, {name: row.get(column) for name, column in columns.items()}) for line, row in rows]

def _analyze(config_path):
    config_path = Path(config_path).resolve()
    config = read_json(config_path)
    errors = requirements_errors(config.get('design', {}))
    if errors:
        raise Clarification('; '.join(errors))
    if not filled(config.get('scope')) or not filled(config.get('scope_evidence')):
        raise Clarification('Declare the comparable scope and its real clarification evidence.')
    comparable = config.get('comparability', {})
    if not isinstance(comparable, dict) or comparable.get('status') != 'confirmed' or not all(filled(comparable.get(key)) for key in ('window_basis', 'evidence')):
        raise Clarification('Confirm comparable observation windows and the source evidence; full and partial periods are not silently mixed.')
    dimensions = config.get('dimensions')
    reserved = {'id', 'metric', 'period', 'unit', 'scope', 'value', 'numerator', 'denominator'}
    if not isinstance(dimensions, list) or not all(filled(item) for item in dimensions) or len(set(dimensions)) != len(dimensions) or set(dimensions) & reserved:
        raise Clarification('dimensions must be unique, explicitly declared field names, or an explicit empty list.')
    if config.get('coverage_policy') != 'require_same_groups':
        raise Clarification('Declare coverage_policy: require_same_groups; missing/new groups are not automatically zero-filled.')
    periods = config.get('periods', {})
    if set(periods) != {'current', 'previous', 'year_ago'} or not filled(periods.get('current')):
        raise Clarification('Declare current, previous, and year_ago labels; use explicit null plus a note for an omitted comparison.')
    notes = config.get('period_notes', {})
    for name, label in periods.items():
        if label is None:
            if name == 'current' or not filled(notes.get(name)):
                raise Clarification(f'Explain the explicitly omitted {name} comparison.')
        elif not filled(label) or (name != 'current' and label == periods['current']):
            raise Clarification('Comparison periods need explicit, distinct-from-current string labels.')
    metrics = config.get('metrics')
    if not isinstance(metrics, list) or not metrics:
        raise Clarification('Declare at least one metric contract.')
    definitions = {}
    for metric in metrics:
        key = metric.get('id', '')
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', key) or key in definitions:
            raise Clarification('Metric IDs must be unique lowercase identifiers.')
        if not all(filled(metric.get(field)) for field in ('label', 'unit', 'definition', 'definition_evidence', 'target_evidence')):
            raise Clarification(f'{key}: label, unit, definition, and actual definition/target evidence are required.')
        if metric.get('kind') not in ('additive', 'ratio') or metric.get('direction') not in ('higher', 'lower', 'neutral'):
            raise Clarification(f'{key}: declare additive/ratio and higher/lower/neutral; other aggregations need a separate explicit method.')
        if 'target' not in metric:
            raise Clarification(f'{key}: declare a target or explicit null with a target_note.')
        if metric['target'] is None:
            if not filled(metric.get('target_note')):
                raise Clarification(f'{key}: explain why target comparison is omitted.')
        else:
            metric['_target'] = number(metric['target'], key + '.target')
        if metric['kind'] == 'ratio':
            if metric['unit'] != 'ratio':
                raise Clarification(f'{key}: dimensionless fraction metrics must explicitly use unit: ratio; physical-unit ratios need a separate method.')
            if metric.get('ratio_bounds') not in ('zero_to_one', 'nonnegative'):
                raise Clarification(f'{key}: declare ratio_bounds; never average row percentages.')
            if metric.get('_target') is not None and (metric['_target'] < 0 or (metric['ratio_bounds'] == 'zero_to_one' and metric['_target'] > 1)):
                raise Clarification(f'{key}: ratio targets use fractions and must satisfy the declared bounds.')
        definitions[key] = metric
    bridges = config.get('bridges', [])
    if not isinstance(bridges, list):
        raise Clarification('bridges must be an explicit list, or omitted when no target-gap bridge is computed.')
    bridge_specs = {}
    for bridge in bridges:
        identity = bridge.get('id', '') if isinstance(bridge, dict) else ''
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', identity) or identity in bridge_specs:
            raise Clarification('Bridge IDs must be unique lowercase identifiers.')
        result = definitions.get(bridge.get('result_metric'))
        if result is None or result['kind'] != 'additive' or result.get('_target') is None:
            raise Clarification(f'{identity}: bridge result must be an additive metric with a declared target.')
        components = bridge.get('components')
        if not isinstance(components, list) or not components:
            raise Clarification(f'{identity}: declare at least one bridge component.')
        normalized, seen = [], set()
        for component in components:
            cid = component.get('id', '') if isinstance(component, dict) else ''
            if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', cid) or cid in seen:
                raise Clarification(f'{identity}: component IDs must be unique lowercase identifiers.')
            if cid in ('gap','closure'):
                raise Clarification(f'{identity}: component IDs gap/closure are reserved for bridge totals, not drivers.')
            seen.add(cid)
            kind = component.get('kind')
            allowed = {'gap_times_target_rate': ('driver_metric', 'rate_metric'),
                       'rate_gap_times_current_level': ('rate_metric', 'level_metric'),
                       'target_minus_current': ('driver_metric',)}
            if kind not in allowed:
                raise Clarification(f'{identity}/{cid}: unsupported bridge formula; use gap_times_target_rate, rate_gap_times_current_level, or target_minus_current.')
            refs = {}
            for field in allowed[kind]:
                metric = definitions.get(component.get(field))
                if metric is None or metric.get('_target') is None:
                    raise Clarification(f'{identity}/{cid}: {field} must name a declared metric with a target.')
                refs[field] = metric['id']
            if kind == 'gap_times_target_rate' and definitions[refs['rate_metric']]['kind'] != 'ratio':
                raise Clarification(f'{identity}/{cid}: rate_metric must be a ratio metric.')
            if kind == 'rate_gap_times_current_level' and (definitions[refs['rate_metric']]['kind'] != 'ratio' or definitions[refs['level_metric']]['kind'] != 'additive'):
                raise Clarification(f'{identity}/{cid}: needs a ratio rate_metric and an additive level_metric.')
            if kind == 'target_minus_current' and definitions[refs['driver_metric']]['kind'] != 'additive':
                raise Clarification(f'{identity}/{cid}: driver_metric must be additive.')
            amount_field = 'level_metric' if kind=='rate_gap_times_current_level' else 'driver_metric'
            amount = definitions[refs[amount_field]]
            if amount['kind'] != 'additive' or amount['unit'] != result['unit']:
                raise Clarification(f'{identity}/{cid}: bridge amount must be additive and use the result unit; amounts and counts cannot be mixed.')
            normalized.append({'id': cid, 'kind': kind, **refs, 'label': component.get('label', cid)})
        bridge_specs[identity] = {'id': identity, 'result_metric': result['id'], 'components': normalized}
    spec = config.get('input', {})
    columns = spec.get('columns', {})
    required = {'id', 'metric', 'period', 'unit', 'scope', *dimensions}
    if any(metric['kind'] == 'additive' for metric in metrics): required.add('value')
    if any(metric['kind'] == 'ratio' for metric in metrics): required.update(('numerator', 'denominator'))
    if not isinstance(columns, dict) or required - set(columns):
        raise Clarification('Column mapping lacks required identity, scope, dimensions, or metric-value fields.')
    row_key = config.get('row_key')
    if not isinstance(row_key, list) or not row_key or not all(filled(key) for key in row_key) or len(set(row_key)) != len(row_key) or set(row_key) - set(columns):
        raise Clarification('Declare the unique row_key at the confirmed data grain; duplicate rows will be rejected.')
    path, raw_rows = source_rows(spec, config_path.parent)
    records = []
    issues = []
    ids, keys = set(), set()
    wanted_periods = {label for label in periods.values() if label is not None}
    for line, row in raw_rows:
        try:
            for name in ('id', 'metric', 'period', 'unit', 'scope', *dimensions, *row_key):
                if not text(row.get(name)):
                    raise Clarification(f'Row {line}: missing {name}; do not silently discard or fill it.')
            identity = text(row['id'])
            key = tuple(text(row[name]) for name in row_key)
            if identity in ids or key in keys:
                raise Clarification(f'Row {line}: duplicate identity or declared grain; ask which record is valid, do not auto-deduplicate.')
            ids.add(identity); keys.add(key)
            metric_id = text(row['metric'])
            if metric_id not in definitions or text(row['period']) not in wanted_periods:
                raise Clarification(f'Row {line}: metric/period outside the declared comparison set; explicitly scope the input first.')
            metric = definitions[metric_id]
            if text(row['unit']) != metric['unit'] or text(row['scope']) != config['scope']:
                raise Clarification(f'Row {line}: unit or scope mismatch; comparisons are blocked.')
            record = {name: text(row[name]) for name in ('id', 'metric', 'period', *dimensions)}
            if metric['kind'] == 'additive':
                record['value'] = number(row.get('value'), f'Row {line}.value')
            else:
                numerator = number(row.get('numerator'), f'Row {line}.numerator')
                denominator = number(row.get('denominator'), f'Row {line}.denominator')
                if numerator < 0 or denominator < 0 or (denominator == 0 and numerator != 0) or (metric['ratio_bounds'] == 'zero_to_one' and numerator > denominator):
                    raise Clarification(f'Row {line}: ratio numerator/denominator violate the confirmed bounds.')
                record.update(numerator=numerator, denominator=denominator)
            records.append(record)
        except Clarification as error:
            issues.append(str(error))
    for key in definitions:
        for label in wanted_periods:
            group = [row for row in records if row['metric'] == key and row['period'] == label]
            if not group:
                issues.append(f'{key}/{label}: comparison records are missing; no zero substitution.')
        for dimension in dimensions:
            groups = [{row[dimension] for row in records if row['metric'] == key and row['period'] == label} for label in sorted(wanted_periods)]
            if any(group != groups[0] for group in groups[1:]):
                issues.append(f'{key}/{dimension}: group coverage differs across periods; clarify missing/new groups before comparison.')
    report = {'schema_version': '1.0', 'status': 'needs_clarification' if issues else 'ready',
              'source': {'file': str(path), 'sha256': digest(path), 'format': spec['format'], 'record_count': len(raw_rows)},
              'contract': {'file': str(config_path), 'sha256': digest(config_path)}, 'issues': issues, 'facts': [], 'metrics': [],
              'limits': ['Descriptive comparisons and arithmetic contributions are not causal attribution.',
                         'A closed target-gap bridge is a fixed-order arithmetic decomposition, not proof that a component caused the gap.',
                         'Observation-window comparability is declared metadata; raw calendar/sample completeness still requires source review.',
                         'Ratio metrics aggregate numerator/denominator; additive contribution is not computed for ratio changes.',
                         'A zero/negative comparison base has no standard relative growth here; the signed difference remains available.',
                         'Scope/definition/clarification evidence requires review against the actual user conversation.']}
    if issues:
        return report
    facts = report['facts']
    def fact(identity, label, value, unit, rows, basis, reason=None):
        item = {'id': identity, 'label': label, 'value': None if value is None else str(value), 'unit': unit,
                'status': 'not_computable' if value is None else 'computed', 'source_rows': [row['id'] for row in rows],
                'basis': basis}
        if value is None: item['reason'] = reason or 'undefined_input'
        facts.append(item)
        return identity
    def aggregate(rows, metric):
        if metric['kind'] == 'additive': return sum((row['value'] for row in rows), Decimal(0))
        denominator = sum((row['denominator'] for row in rows), Decimal(0))
        return sum((row['numerator'] for row in rows), Decimal(0)) / denominator if denominator else None
    for key, metric in definitions.items():
        groups = {name: [row for row in records if row['metric'] == key and row['period'] == label] for name, label in periods.items() if label is not None}
        values = {name: aggregate(rows, metric) for name, rows in groups.items()}
        unit = metric['unit'] if metric['kind'] == 'additive' else 'ratio'
        summary = {'id': key, 'label': metric['label'], 'kind': metric['kind'], 'direction': metric['direction'], 'unit': unit,
                   'totals': {}, 'comparisons': {}, 'breakdowns': {}}
        basis = 'sum(value)' if metric['kind'] == 'additive' else 'sum(numerator)/sum(denominator)'
        for name, value in values.items():
            summary['totals'][name] = fact(f'{key}.{name}', metric['label'] + '/' + name, value, unit, groups[name], basis, 'zero_denominator')
        current, target = values['current'], metric.get('_target')
        if target is not None:
            summary['target'] = fact(f'{key}.target', '目标值', target, unit, [], 'declared metric target in contract')
            gap = current - target if current is not None else None
            summary['target_gap'] = fact(f'{key}.target_gap', '实际减目标（有符号差额）', gap, unit, groups['current'], 'current-target')
            ratio = current / target if current is not None and current >= 0 and target > 0 else None
            summary['actual_to_target'] = fact(f'{key}.actual_to_target', '目标达成比' if metric['direction'] == 'higher' else '实际/目标（不称达成率）', ratio, 'ratio', groups['current'], 'current/positive_target', 'zero_or_negative_target_or_negative_actual')
            required_improvement = None if gap is None or metric['direction'] == 'neutral' else max(Decimal(0), -gap if metric['direction'] == 'higher' else gap)
            summary['required_improvement'] = fact(f'{key}.required_improvement', '达到目标还需改善量', required_improvement, unit, groups['current'], 'direction-aware remaining gap', 'neutral_direction_or_undefined_actual')
            if metric['kind'] == 'ratio':
                summary['target_gap_percentage_points'] = fact(f'{key}.target_gap_percentage_points', '实际与目标的百分点差', gap * 100 if gap is not None else None, 'pp', groups['current'], '(current_ratio-target_ratio)*100')
                summary['required_improvement_percentage_points'] = fact(f'{key}.required_improvement_percentage_points', '达到目标还需改善的百分点', required_improvement * 100 if required_improvement is not None else None, 'pp', groups['current'], 'direction-aware ratio gap * 100', 'neutral_direction_or_undefined_actual')
        for comparison in ('previous', 'year_ago'):
            if comparison not in groups: continue
            base_value = values[comparison]
            rows = groups[comparison] + groups['current']
            delta = current - base_value if current is not None and base_value is not None else None
            growth = delta / base_value if delta is not None and base_value > 0 else None
            comparison_facts = {
                'delta': fact(f'{key}.{comparison}.delta', '本期减比较期', delta, unit, rows, 'current-base'),
                'relative_change': fact(f'{key}.{comparison}.relative_change', '相对变化率', growth, 'ratio', rows, '(current-base)/positive_base', 'zero_or_negative_base_or_undefined_ratio'),
            }
            if metric['kind'] == 'ratio':
                comparison_facts['percentage_points'] = fact(f'{key}.{comparison}.percentage_points', '比率百分点变化', delta * 100 if delta is not None else None, 'pp', rows, '(current_ratio-base_ratio)*100')
            summary['comparisons'][comparison] = comparison_facts
            for dimension in dimensions:
                breakdown = []
                changes = []
                for position, label in enumerate(sorted({row[dimension] for row in groups['current']})):
                    now_rows = [row for row in groups['current'] if row[dimension] == label]
                    then_rows = [row for row in groups[comparison] if row[dimension] == label]
                    now, then = aggregate(now_rows, metric), aggregate(then_rows, metric)
                    change = now - then if now is not None and then is not None else None
                    prefix = f'{key}.{comparison}.{dimension}.{position}'
                    entry = {'group': label,
                             'current': fact(prefix + '.current', label + '/本期', now, unit, now_rows, basis),
                             'base': fact(prefix + '.base', label + '/比较期', then, unit, then_rows, basis),
                             'delta': fact(prefix + '.delta', label + '/变化额', change, unit, then_rows + now_rows, 'group_current-group_base')}
                    if metric['kind'] == 'additive':
                        changes.append(change)
                        share = change / delta if delta else None
                        entry['net_change_share'] = fact(prefix + '.net_change_share', label + '/净变化贡献份额（非因果）', share, 'ratio', then_rows + now_rows, 'group_delta/total_delta; signed shares may exceed 100%', 'zero_net_change')
                    breakdown.append(entry)
                if metric['kind'] == 'additive' and sum(changes, Decimal(0)) != delta:
                    raise Clarification('Contribution reconciliation failed; do not publish inconsistent arithmetic.')
                summary['breakdowns'].setdefault(comparison, {})[dimension] = breakdown
        report['metrics'].append(summary)
    def current_total(key):
        rows=[row for row in records if row['metric']==key and row['period']==periods['current']]
        return aggregate(rows,definitions[key])
    if bridge_specs:
        report['bridges']=[]
        for identity,spec in bridge_specs.items():
            result_metric=definitions[spec['result_metric']]
            values=[]
            for component in spec['components']:
                if component['kind']=='gap_times_target_rate':
                    driver=definitions[component['driver_metric']]
                    value=(current_total(driver['id'])-driver['_target'])*definitions[component['rate_metric']]['_target']
                    basis=f"({driver['id']}.current-{driver['id']}.target)*{component['rate_metric']}.target"
                elif component['kind']=='rate_gap_times_current_level':
                    rate=definitions[component['rate_metric']]
                    value=(current_total(rate['id'])-rate['_target'])*current_total(component['level_metric'])
                    basis=f"({rate['id']}.current-{rate['id']}.target)*{component['level_metric']}.current"
                else:
                    driver=definitions[component['driver_metric']]
                    value=driver['_target']-current_total(driver['id'])
                    basis=f"{driver['id']}.target-{driver['id']}.current"
                values.append(value)
                fact(f"bridge.{identity}.{component['id']}",'目标差距桥接项/'+component['label'],value,result_metric['unit'],[],basis)
            gap=current_total(result_metric['id'])-result_metric['_target']
            closure=gap-sum(values,Decimal(0))
            # Decimal context rounds repeating ratios; only exact algebraic closure counts.
            if abs(closure)>Decimal('1e-18'):
                raise Clarification(f'{identity}: bridge does not close to the result gap; residual {closure}. Add the missing component instead of presenting a partial attribution.')
            closure=Decimal(0)
            fact(f'bridge.{identity}.gap','目标差距合计',gap,result_metric['unit'],[],'result.current-result.target')
            fact(f'bridge.{identity}.closure','桥接闭合差额（应为0）',closure,result_metric['unit'],[],'gap-sum(components)')
            report['bridges'].append({'id':identity,'result_metric':result_metric['id'],
                                      'components':[f"bridge.{identity}.{component['id']}" for component in spec['components']],
                                      'gap':f'bridge.{identity}.gap','closure':f'bridge.{identity}.closure'})
    return report

def analyze(config_path):
    try:
        with localcontext() as context:
            context.prec = 50
            return _analyze(config_path)
    except (Clarification, KeyError, TypeError, OSError, UnicodeError, json.JSONDecodeError) as error:
        return {'schema_version': '1.0', 'status': 'needs_clarification', 'issues': [str(error)], 'facts': [], 'metrics': []}

def verify_artifact(path, expected_sha256):
    path = Path(path).resolve()
    if digest(path) != expected_sha256:
        raise Clarification('Analysis artifact hash mismatch; recompute and bind the actual result.')
    artifact = read_json(path)
    if artifact.get('status') != 'ready':
        raise Clarification('Analysis still needs clarification; no report may use its numbers.')
    fresh = analyze(artifact['contract']['file'])
    if fresh != artifact:
        raise Clarification('Analysis no longer matches its source/contract or arithmetic; recompute before generating.')
    return artifact

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists(): parser.error('Output exists; preserve prior evidence and choose a new path.')
    result = analyze(args.config)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'output': str(output.resolve()), 'facts': len(result['facts']), 'issues': result['issues']}, ensure_ascii=False))
    return 0 if result['status'] == 'ready' else 2

if __name__ == '__main__':
    raise SystemExit(main())
