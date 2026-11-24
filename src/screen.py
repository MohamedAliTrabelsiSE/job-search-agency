"""Deterministic screens. No network, no model, no submission.

A posting that says "no visa sponsorship" must not pass because those words
contain "visa sponsorship". Block phrases are removed before offer phrases
are searched.
"""

import datetime
import re

TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


def plain(text):
    return SPACE.sub(" ", TAG.sub(" ", text or "")).strip()


def _has(title, phrases):
    low = (title or "").lower()
    return any(p.lower() in low for p in phrases)


def title_ok(title, rules):
    return _has(title, rules.get("title_allow") or [])


def seniority_blocked(title, rules):
    return _has(title, rules.get("seniority_block") or [])


def location_ok(location, rules):
    return _has(location, rules.get("location_tokens") or [])


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        n = int(value)
        if n > 10_000_000_000:
            n = n / 1000
        try:
            return datetime.datetime.utcfromtimestamp(n).date()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(text).date()
    except ValueError:
        return None


def within_cutoff(value, rules, today=None):
    found = parse_date(value)
    if found is None:
        return False
    today = today or datetime.date.today()
    return found >= today - datetime.timedelta(days=int(rules.get("cutoff_days") or 0))


def classify_sponsorship(text, rules):
    """Return offered, blocked, conflict, or unknown, plus the phrases found."""
    low = plain(text).lower()
    blocks = [p for p in (rules.get("block_phrases") or []) if p.lower() in low]
    masked = low
    for phrase in rules.get("block_phrases") or []:
        masked = masked.replace(phrase.lower(), " ")
    offers = [p for p in (rules.get("sponsorship_phrases") or []) if p.lower() in masked]
    if blocks and offers:
        status = "conflict"
    elif blocks:
        status = "blocked"
    elif offers:
        status = "offered"
    else:
        status = "unknown"
    return {"status": status, "offers": offers, "blocks": blocks}


def classify_worldwide(location, description, rules):
    """A worldwide keep is work from any country. Remote-in-one-country is a block."""
    blob = plain(f"{location} {description}").lower()
    blocks = [p for p in (rules.get("block_phrases") or []) if p.lower() in blob]
    masked = blob
    for phrase in rules.get("block_phrases") or []:
        masked = masked.replace(phrase.lower(), " ")
    offers = [p for p in (rules.get("offer_phrases") or []) if p.lower() in masked]
    loc = plain(location).lower()
    locks = []
    specific = re.search(r"remote\s*[,:\-]\s*\w+", loc)
    if specific and not any(word in loc for word in ("anywhere", "worldwide", "world", "global")):
        locks.append(specific.group(0))
    for token in rules.get("country_lock") or []:
        if token.lower() in ("remote", "worldwide", "anywhere", "global"):
            continue
        if token.lower() in loc:
            locks.append(token)
    if "remote" in loc and locks and not offers:
        blocks = blocks or ["remote in one country"]
    if blocks and offers:
        status = "conflict"
    elif blocks:
        status = "blocked"
    elif offers:
        status = "offered"
    elif "remote" in loc and not locks:
        status = "offered"
        offers = offers or ["remote"]
    else:
        status = "unknown"
    return {"status": status, "offers": offers, "blocks": blocks}
