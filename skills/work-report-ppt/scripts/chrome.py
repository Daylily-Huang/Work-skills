"""Shared slide chrome: one masthead, one data table, used by both render families.

`generate.py` draws the base layouts and `commercial_layouts.py` draws the office_*
layouts. They used to carry separate copies of the header and the table, so a change
to the page furniture had to be made twice and could drift. Every shared piece of
furniture lives here instead; both modules import it.

Nothing in this module knows about a specific layout.
"""
import math

from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

from text_style import set_cjk_font


def px(value):
    """CSS pixel to EMU (96 dpi, matching the layout grid)."""
    return int(value * 9525)


def rgb(value):
    return RGBColor.from_string(str(value).lstrip('#'))


def header(c, title, tag, idx, draft=False):
    """The masthead. Every page in the deck uses this one, whatever draws the body."""
    p = c.p
    c.shape(40, 26, 5, 44, p['accent'])
    c.text(title, 58, 22, 1116, 52, 32,
           p['ink'] if (c.style.startswith('black') or c.style.startswith('red')) else p['primary'],
           True, display=True)
    c.text(tag, 60, 78, 980, 22, 14, p['secondary'])
    c.line(40, 118, 1240, 118, p['secondary'], 1)
    c.line(40, 118, 124, 118, p['accent'], 3.4)
    c.text(f'{idx:02}', 1172, 682, 68, 26, 15, p['secondary'], align=PP_ALIGN.RIGHT)


def data_table(c, heads, rows, x, y, w, h, size=15, head_h=46, note=None, note_color=None):
    """Native table with alternating fills, a bold first column and a row-capacity check.

    The capacity check refuses a table that PowerPoint would silently grow past its
    planned area; shorten the copy or split the page instead of clipping.
    """
    if not heads or not rows or any(len(row) != len(heads) for row in rows):
        raise ValueError('Invalid table data')
    cols = len(heads)
    colw = (w - 24 * cols) / cols
    per = max(1, int((colw - 24) / (size * 1.333)))
    data_h = (h - head_h) / len(rows)
    # PowerPoint compresses cell margins before it clips, so allow the platform's slack (6px)
    # rather than the full top+bottom margin; a stricter estimate rejects tables that do render.
    room = max(1, int((data_h - 6) / (size * 1.9)))
    for row in rows:
        for value in row:
            text = str(value)
            lines = sum(max(1, math.ceil(len(part) / per)) for part in text.split('\n'))
            if lines > room:
                raise ValueError(f'Table cell needs {lines} lines but its row holds {room}; shorten it or split the page: {text[:32]}')
    table = c.s.shapes.add_table(len(rows) + 1, cols, px(x), px(y), px(w), px(h)).table
    table.rows[0].height = Emu(px(head_h))
    for row in list(table.rows)[1:]:
        row.height = Emu(px(data_h))
    p = c.p
    for ri, row in enumerate([heads] + rows):
        for ci, value in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = str(value)
            cell.margin_left = px(14)
            cell.margin_right = px(10)
            cell.margin_top = px(8)
            cell.margin_bottom = px(6)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(p['primary'] if ri == 0 else (p['tint'] if ri % 2 == 0 else p['paper']))
            for paragraph in cell.text_frame.paragraphs:
                set_cjk_font(paragraph.font, c.font)
                paragraph.font.size = Pt(size)
                paragraph.line_spacing = Pt(size * 1.5)
                paragraph.font.bold = ri == 0 or ci == 0
                paragraph.font.color.rgb = rgb('#FFFFFF' if ri == 0 else p['ink'])
                for run in paragraph.runs:
                    set_cjk_font(run.font, c.font)
    if note:
        c.text(note, x, y + h + 14, w - 30, 40, 15, note_color or p['secondary'])
    return table
