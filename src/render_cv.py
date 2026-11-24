# -*- coding: utf-8 -*-
"""Render one job's cv.json into a DOCX, a PDF, and a plain-text copy.

The DOCX is the file in templates/professional.docx with the person's facts
written into it, so the fonts, bullets, and spacing stay those of that file.
The PDF is that same file, for the application. A long list of roles or
projects continues onto the next sheet.
"""
import copy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BLACK = RGBColor(0x00, 0x00, 0x00)
INK = RGBColor(0x2D, 0x2D, 0x2D)
BODY = RGBColor(0x43, 0x43, 0x43)
GRAY = RGBColor(0x66, 0x66, 0x66)
AGENCY_PAGE = "agency"
BODY_SIZE = 15


def page_is_locked(preferences):
    """True until the person has asked Sami for a different page and that request was saved."""
    note = ""
    if isinstance(preferences, dict):
        note = preferences.get("template_override") or ""
    return not str(note).strip()


def refuse_other_layout(cv, preferences=None):
    requested = (cv or {}).get("layout") or AGENCY_PAGE
    if requested != AGENCY_PAGE and page_is_locked(preferences):
        raise ValueError("This resume page is locked. Tell Sami if you want a different layout.")


def _skill_words(tech):
    parts = []
    for label, items in tech or []:
        for bit in str(items).split(","):
            bit = bit.strip()
            if bit and bit not in parts:
                parts.append(bit)
    return parts


def _skill_line(tech):
    return ", ".join(_skill_words(tech))


def _role_line(title, company):
    title = (title or "").strip()
    company = (company or "").strip()
    if title and company:
        return f"{title} | {company}"
    return title or company


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


def _bottom_border(p, color="2D2D2D", size=6):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    pPr.append(pbdr)


def add_hyperlink(paragraph, text, url, size=BODY_SIZE, bold=False, color=(0x43, 0x43, 0x43), underline=False):
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
    _set_font(r, name="Garamond", size=BODY_SIZE, bold=True, color=BLACK)
    _bottom_border(p)
    p.paragraph_format.keep_with_next = True
    return p


def bullet(doc, text, size=11, before=1, after=0, keep=False):
    p = doc.add_paragraph()
    if keep:
        p.paragraph_format.keep_with_next = True
    _spacing(p, before=before, after=after, line=1.0)
    pf = p.paragraph_format
    pf.left_indent = Cm(0.55)
    pf.first_line_indent = Cm(-0.35)
    mark = p.add_run("● ")
    _set_font(mark, name="Arial", size=13, color=BODY)
    r = p.add_run(text)
    _set_font(r, name="Calibri", size=BODY_SIZE, color=BODY)
    return p


def _dated_line(doc, left, right):
    p = doc.add_paragraph()
    _spacing(p, before=8, after=0)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(17.6), WD_TAB_ALIGNMENT.RIGHT)
    r = p.add_run(left)
    _set_font(r, name="Calibri", size=BODY_SIZE, color=INK)
    if right:
        r = p.add_run("\t" + right)
        _set_font(r, name="Calibri", size=BODY_SIZE, color=GRAY)
    p.paragraph_format.keep_with_next = True
    return p


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "professional.docx"


def _body_paras(doc):
    return list(doc.element.body.findall(qn("w:p")))


def _clear_body(doc):
    body = doc.element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def _append(doc, element):
    body = doc.element.body
    sect = body.find(qn("w:sectPr"))
    if sect is not None:
        sect.addprevious(element)
    else:
        body.append(element)


def _fill(proto, parts):
    """Copy a template paragraph and replace its text. A tab is a real tab."""
    new_p = copy.deepcopy(proto)
    runs = [child for child in list(new_p) if child.tag == qn("w:r")]
    for run in runs:
        new_p.remove(run)
    base = runs[0]
    for part in parts:
        run = copy.deepcopy(base)
        for child in list(run):
            if child.tag in (qn("w:t"), qn("w:tab")):
                run.remove(child)
        if part == "\t":
            run.append(OxmlElement("w:tab"))
        else:
            text = OxmlElement("w:t")
            text.set(qn("xml:space"), "preserve")
            text.text = "" if part is None else str(part)
            run.append(text)
        new_p.append(run)
    return new_p


# The template line is about 10,000 twips wide. Calibri at 11pt is about 100 twips a letter.
LINE_BUDGET = 10500
SKILL_GAP = 640


def _text_twips(text):
    return max(len(text or ""), 1) * 100


def _contact_bits(cv):
    bits = []
    for line in cv.get("contact") or []:
        for seg in line:
            if isinstance(seg, tuple) and seg[0] == "link":
                url = seg[2] or ""
                for prefix in ("https://", "http://"):
                    if url.startswith(prefix):
                        url = url[len(prefix):]
                bits.append(url or seg[1])
            elif str(seg).strip():
                bits.append(str(seg).strip())
    return bits


def _pack_contact(bits):
    """Keep each contact line on the page. A long list continues on the next line."""
    rows = []
    row = []
    width = 0
    sep = "  |  "
    sep_w = _text_twips(sep)
    for bit in bits:
        extra = _text_twips(bit) if not row else sep_w + _text_twips(bit)
        if row and width + extra > LINE_BUDGET:
            rows.append(sep.join(row))
            row = []
            width = 0
            extra = _text_twips(bit)
        row.append(bit)
        width += extra
    if row:
        rows.append(sep.join(row))
    return rows


def _contact_text(cv):
    return "\n".join(_pack_contact(_contact_bits(cv)))


def _pack_skills(words):
    """Fill each skills row. Three wide columns leave a hole between short names."""
    rows = []
    row = []
    width = 0
    for word in words:
        extra = _text_twips(word) if not row else SKILL_GAP + _text_twips(word)
        if row and width + extra > LINE_BUDGET:
            rows.append(row)
            row = [word]
            width = _text_twips(word)
        else:
            row.append(word)
            width += extra
    if row:
        rows.append(row)
    return rows


def _set_tabs(paragraph, positions):
    ppr = paragraph.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr")
        paragraph.insert(0, ppr)
    old = ppr.find(qn("w:tabs"))
    if old is not None:
        ppr.remove(old)
    if not positions:
        return
    tabs = OxmlElement("w:tabs")
    for pos in positions:
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "left")
        tab.set(qn("w:pos"), str(int(pos)))
        tabs.append(tab)
    ppr.insert(0, tabs)


def _header_name(name):
    """Capitals, with a normal space between words. Letter-spacing makes a long name overflow."""
    return " ".join(word for word in (name or "").split() if word).upper()


def _replace_first_text(paragraphs, new_text):
    lines = new_text.split("\n") if isinstance(new_text, str) else list(new_text)
    if not lines:
        return False
    for paragraph in paragraphs:
        for run in paragraph.runs:
            node = run._element.find(qn("w:t"))
            if node is not None and (node.text or "").strip():
                node.text = lines[0]
                for extra in lines[1:]:
                    run._element.append(OxmlElement("w:br"))
                    text = OxmlElement("w:t")
                    text.set(qn("xml:space"), "preserve")
                    text.text = extra
                    run._element.append(text)
                return True
    return False


def _tighten_header(part):
    """The template banner is 23pt. On the next sheet that name eats the page."""
    hdr = part._element
    for tag in ("w:sz", "w:szCs"):
        for node in hdr.iter(qn(tag)):
            if node.get(qn("w:val")) == "46":
                node.set(qn("w:val"), "22")
    seen_rule = False
    for paragraph in [child for child in list(hdr) if child.tag == qn("w:p")]:
        has_rule = paragraph.find(".//" + qn("w:pict")) is not None
        if seen_rule:
            hdr.remove(paragraph)
        elif has_rule:
            seen_rule = True


def _apply_frame(doc, cv):
    """The template keeps a sample name in the header and a sample line in the footer."""
    spaced = _header_name(cv.get("name") or "")
    contact = _contact_text(cv)
    for section in doc.sections:
        headers = (section.header, section.first_page_header, section.even_page_header)
        footers = (section.footer, section.first_page_footer, section.even_page_footer)
        for part in headers:
            if part is not None and spaced and _replace_first_text(part.paragraphs, spaced):
                _tighten_header(part)
        for part in footers:
            if part is not None and contact:
                _replace_first_text(part.paragraphs, contact)


def _dated_parts(left, right):
    if (right or "").strip():
        return [left, "\t", right]
    return [left]


def build(cv, out_path):
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Missing resume template: {TEMPLATE}")
    doc = Document(str(TEMPLATE))
    saved = _body_paras(doc)
    proto = {
        "name": copy.deepcopy(saved[0]),
        "after_name": copy.deepcopy(saved[1]),
        "title": copy.deepcopy(saved[2]),
        "after_title": copy.deepcopy(saved[3]),
        "before_contact": copy.deepcopy(saved[4]),
        "contact": copy.deepcopy(saved[5]),
        "after_contact": copy.deepcopy(saved[6]),
        "before_heading": copy.deepcopy(saved[7]),
        "heading": copy.deepcopy(saved[8]),
        "body": copy.deepcopy(saved[10]),
        "gap": copy.deepcopy(saved[13]),
        "role": copy.deepcopy(saved[14]),
        "bullet": copy.deepcopy(saved[15]),
        "between": copy.deepcopy(saved[19]),
        "before_section": copy.deepcopy(saved[11]),
        "skills": copy.deepcopy(saved[38]),
    }
    _clear_body(doc)

    def add(element):
        _append(doc, element)

    opened = {"yes": False}

    def heading(text):
        if opened["yes"]:
            add(copy.deepcopy(proto["before_section"]))
        opened["yes"] = True
        add(_fill(proto["heading"], [text]))
        add(copy.deepcopy(proto["gap"]))

    add(_fill(proto["name"], [cv["name"]]))
    add(copy.deepcopy(proto["after_name"]))
    if cv.get("headline"):
        add(_fill(proto["title"], [cv["headline"]]))
        add(copy.deepcopy(proto["after_title"]))
    add(copy.deepcopy(proto["before_contact"]))
    for line in _pack_contact(_contact_bits(cv)):
        add(_fill(proto["contact"], [line]))
    add(copy.deepcopy(proto["after_contact"]))
    add(copy.deepcopy(proto["before_heading"]))

    overview = (cv.get("summary") or "").strip() or (cv.get("work_right") or "").strip()
    if overview:
        heading("PROFESSIONAL   OVERVIEW")
        add(_fill(proto["body"], [overview]))

    if cv.get("experience"):
        heading("WORK   EXPERIENCE")
        jobs = cv["experience"]
        for index, job in enumerate(jobs):
            add(_fill(proto["role"], _dated_parts(
                _role_line(job.get("title"), job.get("company")),
                job.get("dates") or "",
            )))
            for item in job.get("bullets") or []:
                add(_fill(proto["bullet"], [item]))
            if index != len(jobs) - 1:
                add(copy.deepcopy(proto["between"]))

    if cv.get("projects"):
        heading("PROJECTS")
        projects = cv["projects"]
        for index, proj in enumerate(projects):
            add(_fill(proto["role"], [proj.get("name") or ""]))
            if (proj.get("stack") or "").strip():
                add(_fill(proto["body"], [proj["stack"].strip()]))
            if (proj.get("tagline") or "").strip():
                add(_fill(proto["body"], [proj["tagline"].strip()]))
            for item in proj.get("bullets") or []:
                add(_fill(proto["bullet"], [item]))
            if index != len(projects) - 1:
                add(copy.deepcopy(proto["between"]))

    if cv.get("education"):
        heading("EDUCATION")
        for ed in cv["education"]:
            add(_fill(proto["role"], _dated_parts(
                _role_line(ed.get("degree"), ed.get("school")),
                ed.get("dates") or "",
            )))

    skills = _skill_words(cv.get("tech"))
    if skills:
        heading("SKILLS")
        for row in _pack_skills(skills):
            parts = []
            positions = []
            cursor = 0
            for index, word in enumerate(row):
                if index:
                    cursor += SKILL_GAP
                    positions.append(cursor)
                    parts.append("\t")
                parts.append(word)
                cursor += _text_twips(word)
            row_el = _fill(proto["skills"], parts)
            _set_tabs(row_el, positions)
            add(row_el)

    if (cv.get("languages") or "").strip():
        heading("LANGUAGES")
        add(_fill(proto["body"], [cv["languages"].strip()]))

    if (cv.get("activities") or "").strip():
        heading("ACTIVITIES")
        add(_fill(proto["body"], [cv["activities"].strip()]))

    _apply_frame(doc, cv)
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
    overview = (cv.get("summary") or "").strip() or (cv.get("work_right") or "").strip()
    if overview:
        lines.append("")
        lines.append("PROFESSIONAL OVERVIEW")
        lines.append(overview)
    lines.append("")

    if cv.get("experience"):
        lines.append("WORK EXPERIENCE")
        for job in cv["experience"]:
            left = _role_line(job.get("title"), job.get("company"))
            lines.append(f'{left}    {job.get("dates") or ""}'.rstrip())
            for item in job.get("bullets") or []:
                lines.append(f"• {item}")
            lines.append("")

    if cv.get("projects"):
        lines.append("PROJECTS")
        for proj in cv["projects"]:
            link = f' ({proj["link"][1]})' if proj.get("link") else ""
            lines.append(f"{_role_line(proj.get('name'), proj.get('stack'))}{link}")
            if (proj.get("tagline") or "").strip():
                lines.append(proj["tagline"])
            for item in proj.get("bullets") or []:
                lines.append(f"• {item}")
            lines.append("")

    if cv.get("education"):
        lines.append("EDUCATION")
        for ed in cv["education"]:
            lines.append(f'{_role_line(ed.get("degree"), ed.get("school"))}    {ed.get("dates") or ""}'.rstrip())
            lines.append("")

    skills = _skill_line(cv.get("tech"))
    if skills:
        lines.append("SKILLS")
        lines.append(skills)
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


def find_soffice():
    """LibreOffice writes the PDF. Word is the other converter."""
    found = shutil.which("soffice") or shutil.which("soffice.exe")
    if found:
        return found
    roots = [
        os_programs(),
        os_programs(x86=True),
        Path.home() / "AppData" / "Local" / "Programs",
        Path.home() / "AppData" / "Local",
    ]
    for root in roots:
        for name in ("soffice.exe", "soffice.com", "soffice"):
            path = root / "LibreOffice" / "program" / name
            if path.is_file():
                return str(path)
    return None


def os_programs(x86=False):
    if x86:
        return Path(r"C:\Program Files (x86)")
    return Path(r"C:\Program Files")


def _soffice_command(soffice, docx_path, profile):
    return [
        soffice,
        "--headless",
        f"-env:UserInstallation={Path(profile).resolve().as_uri()}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(Path(docx_path).parent),
        str(docx_path),
    ]


def _convert_with_soffice(soffice, docx_path):
    profile = Path(tempfile.mkdtemp(prefix="resume-pdf-"))
    command = _soffice_command(soffice, docx_path, profile)
    subprocess.run(command, check=True, timeout=180, capture_output=True)


def _convert_with_word(docx_path, pdf_path):
    if sys.platform != "win32":
        return False
    try:
        import win32com.client
    except ImportError:
        return False
    word = None
    document = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        document = word.Documents.Open(str(Path(docx_path).resolve()))
        document.SaveAs2(str(Path(pdf_path).resolve()), FileFormat=17)
        return pdf_path.is_file()
    except Exception:
        return False
    finally:
        if document is not None:
            document.Close(False)
        if word is not None:
            word.Quit()


def to_pdf(docx_path):
    """Write resume.pdf beside the docx. The PDF is the file to apply with."""
    docx_path = Path(docx_path)
    pdf_path = docx_path.with_suffix(".pdf")
    soffice = find_soffice()
    if soffice:
        _convert_with_soffice(soffice, docx_path)
    elif not _convert_with_word(docx_path, pdf_path):
        raise RuntimeError(
            "Could not write resume.pdf. Install LibreOffice or Microsoft Word. "
            "The page is still in resume.docx."
        )
    if not pdf_path.is_file():
        raise RuntimeError("The converter did not write resume.pdf.")
    return pdf_path


def render_files(cv, out_dir, preferences=None):
    refuse_other_layout(cv, preferences)
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    docx_path = folder / "resume.docx"
    text_path = folder / "resume.txt"
    ready = normalize(cv)
    build(ready, str(docx_path))
    text_path.write_text(to_text(ready), encoding="utf-8")
    pdf_path = to_pdf(docx_path)
    return docx_path, text_path, pdf_path


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path as _Path

    if len(sys.argv) != 3:
        sys.stderr.write("usage: py -3 src/render_cv.py cv.json out_dir\n")
        sys.exit(2)
    payload = json.loads(_Path(sys.argv[1]).read_text(encoding="utf-8"))
    prefs_path = _Path(__file__).resolve().parents[1] / "data" / "preferences.json"
    preferences = json.loads(prefs_path.read_text(encoding="utf-8")) if prefs_path.exists() else None
    docx_path, text_path, pdf_path = render_files(payload, sys.argv[2], preferences)
    print(docx_path)
    print(text_path)
    print(pdf_path)
