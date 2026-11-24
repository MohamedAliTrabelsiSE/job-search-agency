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
            "bullets": bullets[:4] or bullets,
            "stack": job.get("stack") or "",
        })

    projects = []
    ranked_projects = sorted(
        facts.get("projects") or [],
        key=lambda proj: len(_words(" ".join(proj.get("bullets") or [])) & target),
        reverse=True,
    )
    for proj in ranked_projects[:3]:
        item = {
            "name": proj["name"],
            "tagline": proj.get("tagline") or "",
            "bullets": _rank(list(proj.get("bullets") or []), target)[:3],
            "stack": proj.get("stack") or "",
        }
        if proj.get("link"):
            item["link"] = proj["link"]
        projects.append(item)

    links = []
    for link in facts.get("links") or []:
        links.append({"text": link["text"], "url": link["url"]})
    contact_bits = [part for part in (facts.get("location"), facts.get("email"), facts.get("phone")) if part]
    contact = [contact_bits] if contact_bits else []
    if links:
        contact.append(links)

    headline = facts.get("headline_default") or "Software Engineer"

    return {
        "name": facts["name"],
        "headline": headline,
        "contact": contact,
        "work_right": right,
        "summary": ". ".join(part for part in (headline, right) if part),
        "tech": facts.get("tech") or [],
        "experience": experience,
        "projects": projects,
        "education": facts.get("education") or [],
        "languages": facts.get("languages") or "",
        "activities": facts.get("activities") or "",
    }
