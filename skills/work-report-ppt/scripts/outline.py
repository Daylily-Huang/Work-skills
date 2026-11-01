"""Produce a reviewable report outline before presentation rendering."""
from pathlib import Path
import argparse
import json
from design_gate import requirements_errors
from plan_gate import validate as page_errors
from report_logic import prepare
from analyze import digest
from review_outline import render_text

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--analysis', help='Bind an actual ready analysis artifact; its source and arithmetic are verified.')
    parser.add_argument('--plan-output', help='Save the bound, reviewable plan beside the input plan.')
    args = parser.parse_args()
    source, destination = Path(args.input), Path(args.output)
    if destination.exists(): parser.error('Output exists; preserve the reviewed outline.')
    plan_output = Path(args.plan_output).resolve() if args.plan_output else None
    if plan_output and (plan_output.exists() or plan_output.parent != source.resolve().parent or plan_output == destination.resolve()):
        parser.error('plan-output must be a new file beside the input plan, so relative sources keep their meaning.')
    doc = json.loads(source.read_text(encoding='utf-8-sig'))
    if args.analysis:
        analysis = Path(args.analysis).resolve()
        if not isinstance(doc.get('narrative'), dict): parser.error('A narrative plan is required before analysis can be bound.')
        doc['narrative']['analysis'] = {'file': str(analysis), 'sha256': digest(analysis)}
    errors = requirements_errors(doc.get('design', {})) + page_errors(doc.get('slides', []))
    if errors:
        print(json.dumps({'ready': False, 'errors': errors}, ensure_ascii=False, indent=2))
        return 2
    bound, errors, audit = prepare(doc, source.resolve().parent)
    if errors:
        print(json.dumps({'ready': False, 'errors': errors}, ensure_ascii=False, indent=2))
        return 2
    outline_text = render_text(bound, audit)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if plan_output:
        with plan_output.open('x', encoding='utf-8') as stream:
            json.dump(bound, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    with destination.open('x', encoding='utf-8') as stream: stream.write(outline_text)
    print(json.dumps({'ready': True, 'outline': str(destination.resolve()), 'bindings': len(audit['bindings']), 'semantic_review': 'required',
                      'prepared_plan': str(plan_output.resolve()) if plan_output else None,
                      'prepared_plan_sha256': digest(plan_output) if plan_output else None,
                      'next': 'After the user reviews the outline, record approval with scripts/approve_plan.py before generating.'}, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
