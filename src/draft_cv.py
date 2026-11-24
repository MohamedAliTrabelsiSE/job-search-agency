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


def _clean_stack(facts, stack):
    banned = {skill.lower() for skill in facts.get("never_add") or []}
    kept = []
    for bit in str(stack or "").split(","):
        bit = bit.strip()
        if bit and bit.lower() not in banned and bit not in kept:
            kept.append(bit)
    return ", ".join(kept)


def _join_names(items):
    items = [item for item in items if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _overview(facts, target, right, experience, projects):
    headline = facts.get("headline_default") or "Software Engineer"
    closest = []
    rest = []
    for job in experience:
        blob = " ".join(part for part in (job.get("title"), job.get("company"), job.get("stack")) if part)
        if target and (_words(blob) & target):
            closest.append(job)
        else:
            rest.append(job)

    def role_phrase(job):
        place = job.get("title") or "a role"
        if job.get("company"):
            place = f"{place} at {job['company']}"
        stack = _clean_stack(facts, job.get("stack"))
        if stack:
            place = f"{place}, using {stack}"
        return place

    sentences = [_sentence(headline)]
    roles = [_join_names([role_phrase(job) for job in closest + rest])]
    if roles[0]:
        sentences.append(_sentence(f"Work includes {roles[0]}"))
    names = _join_names([proj.get("name") or "" for proj in projects or []])
    if names:
        sentences.append(_sentence(f"Projects include {names}"))
    if right:
        sentences.append(_sentence(right))
    return " ".join(sentence for sentence in sentences if sentence)


def draft(facts, preferences, card):
    target = _words(f"{card.get('title') or ''} {card.get('description') or card.get('excerpt') or ''}")
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
        if proj.get('status'):
            item['status'] = proj['status']
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
        "summary": _overview(facts, target, right, experience, projects),
        "tech": [["", ", ".join(skills)]] if skills else [],
        "experience": experience,
        "projects": projects,
        "education": facts.get("education") or [],
        "languages": facts.get("languages") or "",
        "activities": facts.get("activities") or "",
        "claim_sources": {
            'experience': [{'company':job['company'], 'source':'cv_facts.experience', 'bullets':list(job.get('bullets') or [])} for job in experience],
            'projects': [{'name':project['name'], 'source':'cv_facts.projects', 'bullets':list(project.get('bullets') or [])} for project in projects],
        },
    }
