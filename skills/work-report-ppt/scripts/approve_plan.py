"""Record a real user approval for the prepared plan, before generation.

Run this only after the user has actually reviewed the outline. It does not
invent consent; it records the exact quote and freezes the file hashes.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from approval_gate import approval_path_for, digest, reviewed_content_errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, help='prepared plan that will be rendered')
    parser.add_argument('--outline', required=True, help='outline the user reviewed')
    parser.add_argument('--mode', choices=('confirmed', 'delegated'), required=True)
    parser.add_argument('--quote', required=True, help='exact user approval or explicit delegation')
    parser.add_argument('--source', choices=('conversation', 'user_file'), default='conversation')
    parser.add_argument('--output', help='new approval file; defaults beside the plan')
    parser.add_argument('--confirm', action='store_true', help='confirm that the quote is real, not inferred')
    args = parser.parse_args()
    if not args.confirm:
        parser.error('Pass --confirm only after the user really reviewed the plan.')
    plan = Path(args.plan).resolve()
    outline = Path(args.outline).resolve()
    if not plan.exists() or not outline.exists():
        parser.error('Plan and outline must both exist.')
    if outline.parent != plan.parent:
        parser.error('Outline must sit beside the plan so the recorded relative path stays meaningful.')
    errors = reviewed_content_errors(plan, outline)
    if errors: parser.error('; '.join(errors))
    if not args.quote.strip(): parser.error('Approval quote must be nonempty; silence is not consent.')
    destination = Path(args.output).resolve() if args.output else approval_path_for(plan).resolve()
    if destination.exists():
        parser.error('Approval exists; preserve it and choose a new path if the plan changed.')
    record = {
        'schema_version': '1.0',
        'mode': args.mode,
        'evidence': {'quote': args.quote, 'source': args.source},
        'approved_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'plan_file': plan.name,
        'plan_sha256': digest(plan),
        'slide_count': len(json.loads(plan.read_text(encoding='utf-8-sig')).get('slides', [])),
        'reviewed_outline': {'file': outline.name, 'sha256': digest(outline)},
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'approval': str(destination), 'plan_sha256': record['plan_sha256']}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
