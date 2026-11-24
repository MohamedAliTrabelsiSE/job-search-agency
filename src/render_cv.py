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
from docx.enum.text import WD_TAB_ALIGNMENT
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
    _spacing(p, before=12, after=4)
    r = p.add_run(text)
    _set_font(r, size=12, bold=True, color=NAVY)
    _bottom_border(p)
    p.paragraph_format.keep_with_next = True
    return p


def bullet(doc, text, size=11, before=1, after=0, keep=False):
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


def _dated_line(doc, left, right):
    p = doc.add_paragraph()
    _spacing(p, before=8, after=0)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(17.6), WD_TAB_ALIGNMENT.RIGHT)
    r = p.add_run(left)
    _set_font(r, size=12, bold=True, color=NAVY)
    if right:
        r = p.add_run("\t" + right)
        _set_font(r, size=11, color=MIDGREY)
    p.paragraph_format.keep_with_next = True
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
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)

    p = doc.add_paragraph()
    _spacing(p, before=0, after=1)
    r = p.add_run(cv["name"])
    _set_font(r, size=22, bold=True, color=NAVY)

    if cv.get("headline"):
        p = doc.add_paragraph()
        _spacing(p, before=0, after=2)
        r = p.add_run(cv["headline"])
        _set_font(r, size=12, color=NAVY)

    for line in cv.get("contact") or []:
        p = doc.add_paragraph()
        _spacing(p, before=0, after=0)
        for j, seg in enumerate(line):
            if j:
                sep = p.add_run("  |  ")
                _set_font(sep, size=11, color=MIDGREY)
            if isinstance(seg, tuple) and seg[0] == "link":
                add_hyperlink(p, seg[1], seg[2], size=11)
            else:
                r = p.add_run(str(seg))
                _set_font(r, size=11, color=GREY)

    if (cv.get("work_right") or "").strip():
        p = doc.add_paragraph()
        _spacing(p, before=2, after=0)
        r = p.add_run(cv["work_right"].strip())
        _set_font(r, size=11, italic=True, color=GREY)

    if cv.get("experience"):
        section_heading(doc, "Experience")
        for job in cv["experience"]:
            _dated_line(doc, job.get("title") or "", job.get("dates") or "")
            detail = " · ".join(part for part in (job.get("company") or "", job.get("stack") or "") if part)
            if detail:
                p = doc.add_paragraph()
                _spacing(p, before=0, after=1)
                r = p.add_run(detail)
                _set_font(r, size=11, italic=True, color=MIDGREY)
                p.paragraph_format.keep_with_next = True
            for i, item in enumerate(job.get("bullets") or []):
                bullet(doc, item, keep=(i == 0))

    if cv.get("projects"):
        section_heading(doc, "Projects")
        for proj in cv["projects"]:
            p = doc.add_paragraph()
            _spacing(p, before=8, after=0)
            label = proj.get("name") or ""
            if proj.get("stack"):
                label = f"{label} · {proj['stack']}"
            r = p.add_run(label)
            _set_font(r, size=12, bold=True, color=NAVY)
            if proj.get("link"):
                sep = p.add_run("   ")
                _set_font(sep, size=11)
                add_hyperlink(p, proj["link"][0], proj["link"][1], size=11)
            p.paragraph_format.keep_with_next = True
            if (proj.get("tagline") or "").strip():
                p = doc.add_paragraph()
                _spacing(p, before=0, after=1)
                r = p.add_run(proj["tagline"])
                _set_font(r, size=11, italic=True, color=MIDGREY)
                p.paragraph_format.keep_with_next = True
            for i, item in enumerate(proj.get("bullets") or []):
                bullet(doc, item, keep=(i == 0))

    if cv.get("education"):
        section_heading(doc, "Education")
        for ed in cv["education"]:
            _dated_line(doc, ed.get("degree") or "", ed.get("dates") or "")
            if (ed.get("school") or "").strip():
                p = doc.add_paragraph()
                _spacing(p, before=0, after=0)
                r = p.add_run(ed["school"])
                _set_font(r, size=11, italic=True, color=MIDGREY)

    if cv.get("tech"):
        section_heading(doc, "Skills")
        for label, items in cv["tech"]:
            p = doc.add_paragraph()
            _spacing(p, before=1, after=0, line=1.05)
            r = p.add_run(f"{label}: ")
            _set_font(r, size=11, bold=True, color=DARK)
            r = p.add_run(items)
            _set_font(r, size=11, color=DARK)

    if (cv.get("languages") or "").strip():
        section_heading(doc, "Languages")
        p = doc.add_paragraph()
        _spacing(p, before=1, after=0)
        r = p.add_run(cv["languages"].strip())
        _set_font(r, size=11, color=DARK)

    if (cv.get("activities") or "").strip():
        section_heading(doc, "Activities")
        p = doc.add_paragraph()
        _spacing(p, before=1, after=0)
        r = p.add_run(cv["activities"].strip())
        _set_font(r, size=11, color=DARK)

    doc.save(out_path)
    return out_path


def _plain_line(line):
    parts = []
    for seg in line:
        if isinstance(seg, tuple) and seg[0] == "link":
            parts.append(f"{seg[1]}: {seg[2]}")
        else:
            parts.append(str(seg))
    return " | ".join(part for part in parts if part)


def to_text(cv):
    lines = [cv["name"].upper()]
    if cv.get("headline"):
        lines.append(cv["headline"])
    for line in cv.get("contact") or []:
        text = _plain_line(line)
        if text:
            lines.append(text)
    if (cv.get("work_right") or "").strip():
        lines.append(cv["work_right"].strip())
    lines.append("")

    if cv.get("experience"):
        lines.append("EXPERIENCE")
        for job in cv["experience"]:
            lines.append(f'{job.get("title") or ""}    {job.get("dates") or ""}'.rstrip())
            detail = " · ".join(part for part in (job.get("company") or "", job.get("stack") or "") if part)
            if detail:
                lines.append(detail)
            for item in job.get("bullets") or []:
                lines.append(f"- {item}")
            lines.append("")

    if cv.get("projects"):
        lines.append("PROJECTS")
        for proj in cv["projects"]:
            link = f' ({proj["link"][1]})' if proj.get("link") else ""
            label = proj.get("name") or ""
            if proj.get("stack"):
                label = f"{label} · {proj['stack']}"
            lines.append(f"{label}{link}")
            if (proj.get("tagline") or "").strip():
                lines.append(proj["tagline"])
            for item in proj.get("bullets") or []:
                lines.append(f"- {item}")
            lines.append("")

    if cv.get("education"):
        lines.append("EDUCATION")
        for ed in cv["education"]:
            lines.append(f'{ed.get("degree") or ""}    {ed.get("dates") or ""}'.rstrip())
            if (ed.get("school") or "").strip():
                lines.append(ed["school"])
            lines.append("")

    if cv.get("tech"):
        lines.append("SKILLS")
        for label, items in cv["tech"]:
            lines.append(f"{label}: {items}")
        lines.append("")

    if (cv.get("languages") or "").strip():
        lines.append("LANGUAGES")
        lines.append(cv["languages"].strip())
        lines.append("")

    if (cv.get("activities") or "").strip():
        lines.append("ACTIVITIES")
        lines.append(cv["activities"].strip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


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
