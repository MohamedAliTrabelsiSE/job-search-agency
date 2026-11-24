"""Mechanical half of the ATS specialist.

A pass here means the draft did not invent an employer, a school, or a
forbidden tool, and the visa line matches the path. Wording quality is the
prompt in prompts/ats.md, not this file.
"""

import json
import re


def _blob(cv):
    return json.dumps(cv, ensure_ascii=False).lower()


def findings(cv, facts, card, preferences=None):
    text = _blob(cv)
    found = []
    def flag(severity, quote, action):
        found.append({'severity':severity, 'quote':quote, 'action':action})
    if cv.get('name') != facts.get('name') or cv.get('headline') != facts.get('headline_default'):
        flag('factual', 'identity or headline', 'restore the confirmed identity and headline')
    # Conservative automation: bullets must be exact confirmed claims. An agent
    # may propose rewording, but it needs separate factual review before passing.
    for section, key, fields in (
        ('experience','company',('title','dates','stack')),
        ('projects','name',('stack','tagline','status')),
        ('education','degree',('school','dates')),
    ):
        identity_fields = ('company','title','dates') if section == 'experience' else ('degree','school','dates') if section == 'education' else ('name',)
        def identity(item):
            return tuple(item.get(field) for field in identity_fields)
        source = {identity(item): item for item in facts.get(section) or []}
        items = cv.get(section) or []
        if len(items) != len(facts.get(section) or []) or {identity(item) for item in items} != set(source):
            flag('coverage', section, 'restore every confirmed entry exactly once')
        for item in items:
            original = source.get(identity(item))
            if not original:
                flag('factual', f'{section} identity', 'restore the confirmed entry identity, dates and title')
                continue
            for field in fields:
                if (item.get(field) or '') != (original.get(field) or ''):
                    flag('factual', f'{section}.{item.get(key)}.{field}', 'restore the field from confirmed facts')
            for bullet in item.get('bullets') or []:
                if bullet not in original.get('bullets', []):
                    flag('factual', bullet, 'restore a confirmed bullet or request factual review of the rewrite')
            if sorted(item.get('bullets') or []) != sorted(original.get('bullets') or []):
                flag('coverage', f'{section}.{item.get(key)}.bullets', 'retain every source bullet once')
    if cv.get('languages') != facts.get('languages'):
        flag('coverage', 'languages', 'restore all confirmed spoken languages')
    if cv.get('activities', '') != facts.get('activities', ''):
        flag('coverage', 'activities', 'restore confirmed activities')
    def skill_bits(rows):
        return {part.strip().casefold() for row in rows or []
                for part in str(row.get('items','') if isinstance(row,dict) else row[1]).split(',') if part.strip()}
    extra = skill_bits(cv.get('tech')) - skill_bits(facts.get('tech'))
    if extra:
        flag('factual', ', '.join(sorted(extra)), 'remove unconfirmed entries from the skills section')
    from matching import skills_in
    known_skills = skills_in(json.dumps({k:facts.get(k) for k in ('tech','experience','projects')}))
    extra_skills = skills_in(_blob(cv)) - known_skills
    if extra_skills:
        flag('factual', ', '.join(sorted(extra_skills)), 'remove skills absent from confirmed facts')
    numbers = set(re.findall(r'\b\d+(?:[.,]\d+)?%?', json.dumps(facts)))
    for number in set(re.findall(r'\b\d+(?:[.,]\d+)?%?', cv.get('summary') or '')) - numbers:
        flag('factual', number, 'remove an unconfirmed number from the overview')
    if len((cv.get('summary') or '').split()) < 20:
        flag('format', 'overview', 'restore the professional overview from the source roles and projects')
    from draft_cv import _overview, _words, _skill_bits
    target = _words(f"{card.get('title') or ''} {card.get('description') or card.get('excerpt') or ''}")
    if cv.get('summary') != _overview(facts, target, cv.get('work_right') or '', cv.get('experience'), cv.get('projects')):
        flag('factual', 'overview provenance', 'regenerate the overview from confirmed fields; review free-form rewrites separately')
    expected_contact = [[part for part in (facts.get('phone'),facts.get('email'),facts.get('location')) if part] + list(facts.get('links') or [])]
    if cv.get('contact') != expected_contact:
        flag('factual', 'contact', 'restore the confirmed contact fields and links')
    if cv.get('layout', 'agency') != 'agency' and not (preferences or {}).get('template_override'):
        flag('format', 'layout', 'use the approved agency layout')
    if preferences:
        path = 'remote' if card.get('path') == 'worldwide' else 'relocation'
        if cv.get('work_right') != preferences.get('work_right', {}).get(path):
            flag('factual', 'work_right', 'restore the confirmed work-right statement')
    for skill in facts.get("never_add") or []:
        if re.search(r"\b" + re.escape(skill.lower()) + r"\b", text):
            found.append({"severity": "never_add", "quote": skill, "action": "delete"})
    email = (facts.get("email") or "").lower()
    if email and email not in text:
        found.append({"severity": "factual", "quote": "email", "action": "restore the email from the general resume"})
    known_jobs = {(job.get("company") or "").lower() for job in facts.get("experience") or []}
    for job in cv.get("experience") or []:
        if (job.get("company") or "").lower() not in known_jobs:
            found.append({"severity": "factual", "quote": job.get("company") or "", "action": "delete the employer; it is not on the general resume"})
    known_projects = {(proj.get("name") or "").lower() for proj in facts.get("projects") or []}
    for proj in cv.get("projects") or []:
        if (proj.get("name") or "").lower() not in known_projects:
            found.append({"severity": "factual", "quote": proj.get("name") or "", "action": "delete the project; it is not on the general resume"})
    known_degrees = {(ed.get("degree") or "").lower() for ed in facts.get("education") or []}
    for ed in cv.get("education") or []:
        if (ed.get("degree") or "").lower() not in known_degrees:
            found.append({"severity": "factual", "quote": ed.get("degree") or "", "action": "delete the degree; it is not on the general resume"})
    if card.get("path") == "worldwide" and re.search(r"\bvisa\b", text):
        found.append({"severity": "factual", "quote": "visa", "action": "remove the visa line; this role is remote, not a move"})
    return found


def revise(cv, issues, facts=None, preferences=None, card=None):
    """One correction pass. Drops bullets and sentences that contain a blocked quote."""
    if facts is not None and preferences is not None and card is not None:
        from draft_cv import draft
        return draft(facts, preferences, card)
    quotes = [issue["quote"].lower() for issue in issues if issue.get("quote")]
    if not quotes:
        return cv

    def dirty(text):
        low = (text or "").lower()
        return any(quote in low for quote in quotes)

    out = json.loads(json.dumps(cv))
    for job in out.get("experience") or []:
        job["bullets"] = [bullet for bullet in job.get("bullets") or [] if not dirty(bullet)]
    for proj in out.get("projects") or []:
        proj["bullets"] = [bullet for bullet in proj.get("bullets") or [] if not dirty(bullet)]
    for field in ("summary", "work_right"):
        if dirty(out.get(field)):
            kept = []
            for sentence in re.split(r"(?<=[.])\s+", out.get(field) or ""):
                if sentence and not dirty(sentence):
                    kept.append(sentence)
            out[field] = " ".join(kept)
    if dirty(json.dumps(out.get("contact"))):
        cleaned = []
        for line in out.get("contact") or []:
            row = []
            for seg in line:
                if isinstance(seg, str) and dirty(seg):
                    continue
                row.append(seg)
            if row:
                cleaned.append(row)
        out["contact"] = cleaned
    return out
