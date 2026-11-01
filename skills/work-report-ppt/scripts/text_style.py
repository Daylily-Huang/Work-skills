"""Write one font name to Latin, East Asian and complex-script slots.

python-pptx's ``font.name`` only writes ``a:latin``. Chinese then falls back to the
theme's East Asian font (usually 宋体), so a declared Microsoft YaHei never reached
the slide. Every text and chart label must use this helper instead.
"""
from __future__ import annotations

from pptx.enum.lang import MSO_LANGUAGE_ID
from pptx.oxml.ns import qn


def set_cjk_font(font, name: str):
    try:
        font.name = name
    except (AttributeError, ValueError):
        return font
    rpr = getattr(font, '_rPr', None)
    if rpr is None:
        return font
    latin = rpr.find(qn('a:latin'))
    if latin is None:
        return font
    anchor = latin
    for tag in ('a:ea', 'a:cs'):
        element = rpr.find(qn(tag))
        if element is None:
            element = rpr.makeelement(qn(tag), {'typeface': name})
            anchor.addnext(element)
        else:
            element.set('typeface', name)
        anchor = element
    try:
        font.language_id = MSO_LANGUAGE_ID.SIMPLIFIED_CHINESE
    except (AttributeError, ValueError):
        pass
    return font
