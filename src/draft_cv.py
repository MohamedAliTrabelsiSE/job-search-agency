"""Build one resume for one job from the general-resume fact pool.

Bullets are copied, never rewritten into new claims. Matching bullets are
moved first. The visa line comes from preferences and is added only on a
relocation card.
"""

import re


def _words(text):
    return {word for word in re.findall(r"[a-z0-9][a-z0-9+.#-]{2,}", (text or "").lower())}


def _rank(items, target):
    scored = []
    for item in items:
        overlap = len(_words(item) & target)
        scored.append((overlap, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    ordered = [item for overlap, item in scored if overlap > 0]
    for _, item in scored:
        if item not in ordered:
            ordered.append(item)
    return ordered


def _sentence(text):
    text = (text or "").strip()
    if not text:
        return ""
    if text[-1] not in ".!?":
        return text + "."
    return text


def _skill_bits(facts):
    banned = {skill.lower() for skill in facts.get("never_add") or []}
    bits = []
    for item in facts.get("tech") or []:
        items = item["items"] if isinstance(item, dict) else item[1]
        for bit in str(items).split(","):
            bit = bit.strip()
            if bit and bit.lower() not in banned and bit not in bits:
                bits.append(bit)
    return bits


def _overview(facts, target, right, experience):
    headline = facts.get("headline_default") or "Software Engineer"
    match = None
    for job in experience:
        blob = " ".join(part for part in (job.get("title"), job.get("company"), job.get("stack")) if part)
        if _words(blob) & target:
            match = job
            break
    sentences = [_sentence(headline)]
    if match:
        place = match["title"]
        if match.get("company"):
            place = f"{match['title']} at {match['company']}"
        line = f"Closest work is {place}"
        stack = (match.get("stack") or "").strip()
        if stack:
            line += f", using {stack}"
        sentences.append(_sentence(line))
    if right:
        sentences.append(_sentence(right))
    return " ".join(sentences[:3])


def draft(facts, preferences, card):
    target = _words(f"{card.get('title') or ''} {card.get('excerpt') or ''}")
    work = preferences.get("work_right") or {}
    if card.get("path") == "worldwide":
        right = work.get("remote") or "Working remotely from the current country."
    else:
        right = work.get("relocation") or "Open to relocation."

    experience = []
    for job in facts.get("experience") or []:
        bullets = _rank(list(job.get("bullets") or []), target)
        experience.append({
            "title": job["title"],
            "dates": job["dates"],
            "company": job["company"],
            "bullets": bullets,
            "stack": job.get("stack") or "",
        })

    projects = []
    ranked_projects = sorted(
        facts.get("projects") or [],
        key=lambda proj: len(_words(" ".join(proj.get("bullets") or [])) & target),
        reverse=True,
    )
    for proj in ranked_projects:
        item = {
            "name": proj["name"],
            "tagline": proj.get("tagline") or "",
            "bullets": _rank(list(proj.get("bullets") or []), target),
            "stack": proj.get("stack") or "",
        }
        if proj.get("link"):
            item["link"] = proj["link"]
        projects.append(item)

    links = []
    for link in facts.get("links") or []:
        links.append({"text": link["text"], "url": link["url"]})
    contact = [[part for part in (facts.get("phone"), facts.get("email"), facts.get("location")) if part] + links]
    contact = [row for row in contact if row]

    headline = facts.get("headline_default") or "Software Engineer"
    skills = _rank(_skill_bits(facts), target)

    return {
        "name": facts["name"],
        "headline": headline,
        "contact": contact,
        "work_right": right,
        "summary": _overview(facts, target, right, experience),
        "tech": [["", ", ".join(skills)]] if skills else [],
        "experience": experience,
        "projects": projects,
        "education": facts.get("education") or [],
        "languages": facts.get("languages") or "",
        "activities": facts.get("activities") or "",
    }
