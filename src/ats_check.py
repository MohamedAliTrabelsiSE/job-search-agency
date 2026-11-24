"""Mechanical half of the ATS specialist.

A pass here means the draft did not invent an employer, a school, or a
forbidden tool, and the visa line matches the path. Wording quality is the
prompt in prompts/ats.md, not this file.
"""

import json
import re


def _blob(cv):
    return json.dumps(cv, ensure_ascii=False).lower()


def findings(cv, facts, card):
    text = _blob(cv)
    found = []
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


def revise(cv, issues):
    """One correction pass. Drops bullets and sentences that contain a blocked quote."""
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
    if dirty(out.get("summary")):
        kept = []
        for sentence in re.split(r"(?<=[.])\s+", out.get("summary") or ""):
            if sentence and not dirty(sentence):
                kept.append(sentence)
        out["summary"] = " ".join(kept)
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
