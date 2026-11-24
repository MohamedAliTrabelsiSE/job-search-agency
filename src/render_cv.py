# -*- coding: utf-8 -*-
"""Render one job's cv.json into a DOCX and a plain-text copy.

The layout is a single column with the contact details in the body, so a
normal applicant-tracking system can read it. Search itself does not need
this module. Rendering needs python-docx.
"""
import copy
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY = RGBColor(0x1F, 0x38, 0x64)
DARK = RGBColor(0x26, 0x26, 0x26)
GREY = RGBColor(0x40, 0x40, 0x40)
MIDGREY = RGBColor(0x59, 0x59, 0x59)
LINK = RGBColor(0x11, 0x55, 0xCC)


def _set_font(run, name="Calibri", size=9.5, bold=False, italic=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(attr), name)


def _spacing(p, before=0, after=0, line=None):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if line is not None:
        pf.line_spacing = line


def _bottom_border(p, color="1F3864", size=8):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    pPr.append(pbdr)


def _letter_spacing(run, twips=24):
    rpr = run._element.get_or_add_rPr()
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:val"), str(twips))
    rpr.append(sp)


def add_hyperlink(paragraph, text, url, size=9.5, bold=False, color=LINK, underline=False):
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rFonts.set(qn(attr), "Calibri")
    rPr.append(rFonts)
    if bold:
        rPr.append(OxmlElement("w:b"))
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(size * 2)))
    rPr.append(sz)
    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "%02X%02X%02X" % (color[0], color[1], color[2]) if isinstance(color, tuple) else str(color))
    rPr.append(c)
    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def section_heading(doc, text):
    p = doc.add_paragraph()
    _spacing(p, before=9, after=4)
    r = p.add_run(text.upper())
    _set_font(r, size=10.5, bold=True, color=NAVY)
    _letter_spacing(r, 26)
    _bottom_border(p)
    p.paragraph_format.keep_with_next = True
    return p


def kv_line(doc, parts, size=10, before=4, after=0):
    """parts: list of (text, bold, italic, color)."""
    p = doc.add_paragraph()
    _spacing(p, before=before, after=after)
    for text, bold, italic, color in parts:
        r = p.add_run(text)
        _set_font(r, size=size, bold=bold, italic=italic, color=color)
    p.paragraph_format.keep_with_next = True
    return p


def bullet(doc, text, size=9.5, before=1, after=0, keep=False):
    p = doc.add_paragraph(style="List Bullet")
    if keep:
        p.paragraph_format.keep_with_next = True
    _spacing(p, before=before, after=after, line=1.0)
    pf = p.paragraph_format
    pf.left_indent = Cm(0.55)
    pf.first_line_indent = Cm(-0.35)
    r = p.add_run(text)
    _set_font(r, size=size, color=DARK)
    return p


def build(cv, out_path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(1.7)
    sec.right_margin = Cm(1.7)
    sec.top_margin = Cm(1.35)
    sec.bottom_margin = Cm(1.3)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(9.5)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)

    # ---------- header ----------
    p = doc.add_paragraph()
    _spacing(p, before=0, after=1)
    r = p.add_run(cv["name"])
    _set_font(r, size=23, bold=True, color=NAVY)

    p = doc.add_paragraph()
    _spacing(p, before=0, after=3)
    r = p.add_run(cv["headline"])
    _set_font(r, size=12, color=NAVY)

    for i, line in enumerate(cv["contact"]):
        p = doc.add_paragraph()
        _spacing(p, before=0, after=0)
        for j, seg in enumerate(line):
            if j:
                sep = p.add_run("  |  ")
                _set_font(sep, size=9, color=MIDGREY)
            if isinstance(seg, tuple) and seg[0] == "link":
                add_hyperlink(p, seg[1], seg[2], size=9)
            else:
                r = p.add_run(seg)
                _set_font(r, size=9, color=GREY)

    # ---------- summary ----------
    if cv.get("summary"):
        section_heading(doc, "Summary")
        p = doc.add_paragraph()
        _spacing(p, before=0, after=0, line=1.05)
        r = p.add_run(cv["summary"])
        _set_font(r, size=9.5, color=DARK)

    # ---------- languages & technologies ----------
    section_heading(doc, "Languages & Technologies")
    for label, items in cv["tech"]:
        p = doc.add_paragraph()
        _spacing(p, before=1, after=0, line=1.0)
        pf = p.paragraph_format
        pf.left_indent = Cm(3.05)
        pf.first_line_indent = Cm(-3.05)
        pf.tab_stops.add_tab_stop(Cm(3.05))
        r = p.add_run(label)
        _set_font(r, size=9.5, color=DARK)
        r = p.add_run("\t")
        _set_font(r, size=9.5, color=DARK)
        r = p.add_run(items)
        _set_font(r, size=9.5, color=DARK)

    # ---------- experience ----------
    section_heading(doc, "Experience")
    for job in cv["experience"]:
        kv_line(
            doc,
            [
                (job["title"], True, False, NAVY),
                ("  ", False, False, DARK),
                (job["dates"], False, False, MIDGREY),
            ],
            size=10,
            before=6,
        )
        p = doc.add_paragraph()
        _spacing(p, before=0, after=1)
        r = p.add_run(job["company"])
        _set_font(r, size=9.5, italic=True, color=MIDGREY)
        p.paragraph_format.keep_with_next = True
        for i, b in enumerate(job["bullets"]):
            bullet(doc, b, keep=(i == 0))
        if job.get("stack"):
            p = doc.add_paragraph()
            _spacing(p, before=1, after=0)
            r = p.add_run("Stack: " + job["stack"])
            _set_font(r, size=8.5, italic=True, color=MIDGREY)

    # ---------- projects ----------
    section_heading(doc, "Projects")
    for proj in cv["projects"]:
        p = doc.add_paragraph()
        _spacing(p, before=5, after=0)
        r = p.add_run(proj["name"])
        _set_font(r, size=10, bold=True, color=NAVY)
        if proj.get("link"):
            sep = p.add_run("   ")
            _set_font(sep, size=9)
            add_hyperlink(p, proj["link"][0], proj["link"][1], size=8.5)
        p.paragraph_format.keep_with_next = True
        p = doc.add_paragraph()
        _spacing(p, before=0, after=1)
        r = p.add_run(proj["tagline"])
        _set_font(r, size=9.5, italic=True, color=MIDGREY)
        p.paragraph_format.keep_with_next = True
        for i, b in enumerate(proj["bullets"]):
            bullet(doc, b, keep=(i == 0))
        if proj.get("stack"):
            p = doc.add_paragraph()
            _spacing(p, before=1, after=0)
            r = p.add_run("Stack: " + proj["stack"])
            _set_font(r, size=8.5, italic=True, color=MIDGREY)

    # ---------- education ----------
    section_heading(doc, "Education")
    for ed in cv["education"]:
        kv_line(
            doc,
            [
                (ed["degree"], True, False, NAVY),
                ("  ", False, False, DARK),
                (ed["dates"], False, False, MIDGREY),
            ],
            size=10,
            before=5,
        )
        p = doc.add_paragraph()
        _spacing(p, before=0, after=0)
        r = p.add_run(ed["school"])
        _set_font(r, size=9.5, italic=True, color=MIDGREY)

    # ---------- languages & activities ----------
    section_heading(doc, "Languages and Activities")
    p = doc.add_paragraph()
    _spacing(p, before=2, after=1)
    r = p.add_run("Languages: ")
    _set_font(r, size=9.5, color=DARK)
    r = p.add_run(cv["languages"])
    _set_font(r, size=9.5, color=DARK)
    p = doc.add_paragraph()
    _spacing(p, before=0, after=0)
    r = p.add_run("Activities: ")
    _set_font(r, size=9.5, color=DARK)
    r = p.add_run(cv["activities"])
    _set_font(r, size=9.5, color=DARK)

    doc.save(out_path)
    return out_path


def to_text(cv):
    L = []
    L.append(cv["name"].upper())
    L.append(cv["headline"])
    for line in cv["contact"]:
        parts = []
        for seg in line:
            if isinstance(seg, tuple) and seg[0] == "link":
                parts.append(f'{seg[1]}: {seg[2]}')
            else:
                parts.append(seg)
        L.append(" | ".join(parts))
    L.append("")
    if cv.get("summary"):
        L.append("SUMMARY")
        L.append(cv["summary"])
        L.append("")
    L.append("LANGUAGES & TECHNOLOGIES")
    for label, items in cv["tech"]:
        L.append(f"{label}: {items}")
    L.append("")
    L.append("EXPERIENCE")
    for job in cv["experience"]:
        L.append(f'{job["title"]} | {job["dates"]}')
        L.append(job["company"])
        for b in job["bullets"]:
            L.append(f"- {b}")
        if job.get("stack"):
            L.append(f'Stack: {job["stack"]}')
        L.append("")
    L.append("PROJECTS")
    for proj in cv["projects"]:
        link = f' ({proj["link"][1]})' if proj.get("link") else ""
        L.append(f'{proj["name"]}{link}')
        L.append(proj["tagline"])
        for b in proj["bullets"]:
            L.append(f"- {b}")
        if proj.get("stack"):
            L.append(f'Stack: {proj["stack"]}')
        L.append("")
    L.append("EDUCATION")
    for ed in cv["education"]:
        L.append(f'{ed["degree"]} | {ed["dates"]}')
        L.append(ed["school"])
        L.append("")
    L.append("LANGUAGES AND ACTIVITIES")
    L.append("Languages: " + cv["languages"])
    L.append("Activities: " + cv["activities"])
    return "\n".join(L)


def normalize(cv):
    """Accept the JSON a writer saves. The renderer uses tuples internally."""
    out = dict(cv)
    contact = []
    for line in cv.get("contact") or []:
        row = []
        for seg in line:
            if isinstance(seg, dict) and seg.get("url"):
                row.append(("link", seg.get("text") or seg["url"], seg["url"]))
            else:
                row.append(seg)
        contact.append(row)
    out["contact"] = contact
    projects = []
    for proj in cv.get("projects") or []:
        item = dict(proj)
        link = item.get("link")
        if isinstance(link, dict) and link.get("url"):
            item["link"] = (link.get("text") or "Link", link["url"])
        elif isinstance(link, list) and len(link) == 2:
            item["link"] = (link[0], link[1])
        projects.append(item)
    out["projects"] = projects
    tech = []
    for item in cv.get("tech") or []:
        if isinstance(item, dict):
            tech.append((item["label"], item["items"]))
        else:
            tech.append((item[0], item[1]))
    out["tech"] = tech
    return out


def render_files(cv, out_dir):
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    docx_path = folder / "resume.docx"
    text_path = folder / "resume.txt"
    ready = normalize(cv)
    build(ready, str(docx_path))
    text_path.write_text(to_text(ready), encoding="utf-8")
    return docx_path, text_path


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path as _Path

    if len(sys.argv) != 3:
        sys.stderr.write("usage: py -3 src/render_cv.py cv.json out_dir\n")
        sys.exit(2)
    payload = json.loads(_Path(sys.argv[1]).read_text(encoding="utf-8"))
    docx_path, text_path = render_files(payload, sys.argv[2])
    print(docx_path)
    print(text_path)
