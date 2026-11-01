"""Require explicit review of the exact prepared plan before rendering.

The sidecar records who approved which file, its SHA256, slide count and the
reviewed outline. A changed plan invalidates the approval automatically.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def reviewed_content_errors(plan, outline):
    """Reject an unrelated/partial outline, while leaving consent authenticity to humans."""
    from report_logic import prepare
    from review_outline import render_text
    try:
        doc = json.loads(Path(plan).read_text(encoding='utf-8-sig'))
        bound, errors, audit = prepare(doc, Path(plan).resolve().parent)
        if errors: return errors
        if Path(outline).read_text(encoding='utf-8-sig') != render_text(bound, audit):
            return ['Reviewed outline does not represent this plan. Regenerate with outline.py and obtain a real review.']
    except (OSError, ValueError, KeyError, TypeError) as error:
        return ['Cannot verify the reviewed outline: '+str(error)]
    return []


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def approval_path_for(plan: Path) -> Path:
    return Path(plan).with_name(Path(plan).name + '.approval.json')


def validate(plan_path, approval_path=None):
    plan = Path(plan_path).resolve()
    record_path = Path(approval_path).resolve() if approval_path else approval_path_for(plan).resolve()
    errors = []
    if not plan.exists():
        return [f'Plan file does not exist: {plan}']
    if not record_path.exists():
        return [f'Plan approval is missing: {record_path}. Review the outline and record the exact approval before generating.']
    try:
        record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError) as error:
        return [f'Plan approval cannot be read: {error}']
    if not isinstance(record, dict):
        return ['Plan approval must be a JSON object.']
    if record.get('mode') not in ('confirmed', 'delegated'):
        errors.append('Plan approval mode must be confirmed or delegated.')
    evidence = record.get('evidence')
    if not isinstance(evidence, dict) or not str(evidence.get('quote', '')).strip() or evidence.get('source') not in ('conversation', 'user_file'):
        errors.append('Plan approval needs the actual approval quote and source=conversation/user_file; silence is not consent.')
    if record.get('plan_file') != plan.name:
        errors.append('Plan approval points to a different file name.')
    if record.get('plan_sha256') != digest(plan):
        errors.append('Plan approval hash does not match the current plan; re-review after any edit.')
    try:
        slides = json.loads(plan.read_text(encoding='utf-8-sig')).get('slides', [])
        count = len(slides)
    except (OSError, json.JSONDecodeError, AttributeError):
        count = -1
        errors.append('Plan file cannot be read for slide-count verification.')
    if record.get('slide_count') != count:
        errors.append('Plan approval covers a different number of slides.')
    outline = record.get('reviewed_outline')
    if not isinstance(outline, dict) or not outline.get('file') or not outline.get('sha256'):
        errors.append('Plan approval must record the reviewed outline file and hash.')
    else:
        outline_path = (plan.parent / outline['file']).resolve()
        if not outline_path.exists():
            errors.append('Reviewed outline file no longer exists.')
        elif digest(outline_path) != outline['sha256']:
            errors.append('Reviewed outline changed after approval; review again.')
        else:
            errors.extend(reviewed_content_errors(plan, outline_path))
    return errors
