"""Check page intent and obvious recycling of a small set of compositions."""
from design_gate import filled

DECORATIVE = {'cover', 'office_cover', 'section', 'closing'}
# These aliases actually render the same composition; renaming them is not variety.
ALIASES = {'agenda': 'contents', 'swot': 'matrix', 'line': 'bar', 'office_org': 'office_wbs'}

def validate(slides):
    if not isinstance(slides, list) or not 1 <= len(slides) <= 100:
        return ['Provide 1–100 individually planned slides.']
    errors = []
    all_pages = []
    for number, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            errors.append(f'Slide {number} must be an individually planned object.')
            continue
        for field in ('layout', 'title', 'purpose', 'layout_reason'):
            if not filled(slide.get(field)):
                errors.append(f'Slide {number} needs {field} in its page plan.')
        if not filled(slide.get('message_claim_id')):
            errors.append(f'Slide {number} needs message_claim_id; the core message is projected from narrative.claims, not written twice.')
        if filled(slide.get('message')):
            errors.append(f'Slide {number}: remove message; a second copy of the conclusion is projected from narrative.claims instead.')
        layout = slide.get('layout')
        if isinstance(layout, str):
            all_pages.append((number, ALIASES.get(layout, layout)))
    # Check substantive pages across chapter covers so covers cannot hide a loop.
    substantive = [(number, layout) for number, layout in all_pages if layout not in DECORATIVE]
    for sequence in (all_pages, substantive):
        for start in range(len(sequence)):
            for period in range(1, 5):
                repeats = 3 if period == 1 else 2
                end = start + period * repeats
                if end > len(sequence):
                    continue
                block = [item[1] for item in sequence[start:start + period]]
                actual = [item[1] for item in sequence[start:end]]
                if actual == block * repeats:
                    errors.append(
                        f'Recycled layout loop on pages {sequence[start][0]}–{sequence[end - 1][0]} '
                        f'(period {period}). Replan compositions for the actual content; '
                        'changing titles, colors, or inserting chapter covers does not resolve the loop.'
                    )
                    return errors
    return errors
