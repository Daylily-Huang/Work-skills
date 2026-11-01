"""Require clarified requirements; no mandatory website review or image generation."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BRIEF_FIELDS = (
    'purpose', 'audience', 'duration_or_pages', 'key_message', 'source_scope',
    'content_constraints', 'design_constraints',
)

def filled(value):
    return isinstance(value, str) and bool(value.strip())

def unresolved(value):
    return filled(value) and value.strip().strip('。.!！?？').casefold() in (
        '待确认', '待补', '待定', '未知', '不确定', '暂定', 'tbd', 'todo', 'unknown', 'unspecified',
    )

def requirements_errors(design):
    """Both drafts and finals must stop at unresolved requirements."""
    if not isinstance(design, dict):
        return ['Design must include a real requirement clarification record.']
    errors = []
    requirements = design.get('requirements', {})
    if not isinstance(requirements, dict):
        return ['Requirements must be a clarification record; ask the user first.']
    if requirements.get('status') != 'clarified':
        errors.append('Requirements are not clarified. Ask the user and wait; do not infer consent.')
    for key in ('open_questions', 'conflicts'):
        value = requirements.get(key)
        if not isinstance(value, list) or value:
            errors.append(f'Requirements {key} must be an explicitly empty list. Resolve every ambiguity with the user first.')
    brief = requirements.get('brief', {})
    evidence = requirements.get('evidence', {})
    for field in BRIEF_FIELDS:
        if not isinstance(brief, dict) or not filled(brief.get(field)):
            errors.append(f'Missing requirement: {field}. Ask the user; do not fill a default.')
        elif unresolved(brief[field]):
            errors.append(f'Unresolved requirement: {field}. Ask the user and wait for clarification.')
        if not isinstance(evidence, dict) or not filled(evidence.get(field)):
            errors.append(f'Missing conversation or supplied-file evidence for requirement: {field}.')
    resolved = requirements.get('resolved_questions', [])
    if not isinstance(resolved, list):
        errors.append('resolved_questions must be a list.')
    else:
        for index, item in enumerate(resolved, 1):
            if not isinstance(item, dict) or not all(filled(item.get(key)) for key in ('question', 'answer', 'evidence')):
                errors.append(f'Clarification {index} needs a real question, user answer, and evidence; an unanswered question cannot pass.')
    return errors

def validate(design, base=None):
    errors = requirements_errors(design)
    if not isinstance(design, dict):
        return errors
    catalog = json.loads((ROOT / 'assets/design-catalog.json').read_text(encoding='utf-8'))
    palettes = json.loads((ROOT / 'assets/palettes.json').read_text(encoding='utf-8'))
    materials = json.loads((ROOT / 'assets/media-library/catalog.json').read_text(encoding='utf-8'))['assets']
    selection = design.get('selection', {})
    if not isinstance(selection, dict):
        return errors + ['Selection must be an object.']
    if selection.get('scenario') not in catalog['scenes']:
        errors.append('Choose a valid scenario after clarification.')
    if selection.get('palette') not in palettes:
        errors.append('Choose one of the ten palettes.')
    if selection.get('template') not in {item['id'] for item in catalog['templates']}:
        errors.append('Choose a base template ID; this sets visual style, not a repeated page sequence.')
    assets = selection.get('assets')
    if not isinstance(assets, list) or not all(isinstance(item, str) for item in assets):
        errors.append('Declare selected asset IDs, including an explicit empty list when none are relevant.')
    elif set(assets) - {item['id'] for item in materials}:
        errors.append('Unknown selected material ID.')
    approval = design.get('approval', {})
    if not isinstance(approval, dict):
        return errors + ['Record the actual selection instruction.']
    if approval.get('mode') not in ('confirmed', 'delegated') or not filled(approval.get('evidence')):
        errors.append('Record actual user selection or explicit delegated selection; no invented confirmation or extra preview approval is needed.')
    fields = approval.get('fields', [])
    if not isinstance(fields, list) or not all(isinstance(item, str) for item in fields) or set(fields) != {'scenario', 'palette', 'template', 'assets'}:
        errors.append('Selection instructions must cover scenario, palette, template, and assets.')
    return errors

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('design')
    args = parser.parse_args()
    path = Path(args.design)
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    problems = validate(data, path.parent)
    print(json.dumps({'ready': not problems, 'errors': problems}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(problems))
