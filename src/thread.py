"""Write the morning handoff as a short thread. Nobody shares a chat."""

from pathlib import Path

from load_config import load_json
from names import ATS, INBOX, LEAD, RANKER, SCOUTS, WRITER
from places import scouts_for

ORDER = ("worldwide", "dach", "benelux-ie", "nordics")


def _line(speaker, listener, text):
    return f"{speaker} → {listener}    {text}"


def _count(number, singular, plural):
    return f"{number} {singular if number == 1 else plural}"


def build_thread(root, reviews):
    root = Path(root)
    data = root / "data"
    lines = ["# This morning", ""]

    inbox_path = data / "inbox.json"
    if not inbox_path.exists():
        lines.append(_line(INBOX, LEAD, "Mail was not read. Nothing sent."))
    else:
        inbox = load_json(inbox_path)
        if inbox.get("skipped"):
            lines.append(_line(INBOX, LEAD, "Mail was not connected. Nothing sent."))
        else:
            rejections = sum(1 for message in inbox.get("messages") or [] if message.get("kind") == "rejection")
            lines.append(_line(INBOX, LEAD, f"{rejections} rejections filed. Nothing sent."))

    preferences_path = data / "preferences.json"
    wanted = scouts_for(load_json(preferences_path)) if preferences_path.exists() else []
    for name in ORDER:
        if name not in wanted:
            continue
        person = SCOUTS[name]
        path = data / f"scout-{name}.json"
        if not path.exists():
            lines.append(_line(person, LEAD, "No report."))
            continue
        payload = load_json(path)
        jobs = payload.get("candidates") or []
        offered = sum(1 for job in jobs if job.get("sponsorship") == "offered")
        lines.append(_line(person, LEAD, f"{_count(len(jobs), 'job', 'jobs')}, {offered} passed the text check."))

    shortlist_path = data / "shortlist.json"
    kept = []
    skipped = []
    if shortlist_path.exists():
        shortlist = load_json(shortlist_path)
        kept = shortlist.get("cards") or []
        skipped = shortlist.get("skipped") or []
    lines.append(_line(
        RANKER,
        WRITER,
        f"{_count(len(kept), 'job', 'jobs')}, best first. {len(skipped)} skipped, no overlap.",
    ))

    passed = 0
    for review in reviews:
        title = review.get("title") or "role"
        company = review.get("company") or "company"
        lines.append(_line(WRITER, ATS, f"resume for {title} at {company}."))
        findings = review.get("findings") or []
        remaining = review.get("remaining") or []
        if not findings:
            passed += 1
            lines.append(_line(ATS, WRITER, "pass. No findings."))
        elif not remaining:
            quotes = ", ".join(item.get("quote") or "a problem" for item in findings)
            passed += 1
            lines.append(_line(ATS, WRITER, f"{quotes}. Maya fixed that once."))
        else:
            quotes = ", ".join(item.get("quote") or "a problem" for item in remaining)
            lines.append(_line(ATS, WRITER, f"{quotes}. Still blocked. No second rewrite."))

    lines.append("")
    lines.append(_line(LEAD, "you", f"{_count(passed, 'folder', 'folders')}. Nothing submitted and nothing sent."))
    return "\n".join(lines) + "\n"


def write_thread(root, reviews):
    text = build_thread(root, reviews)
    path = Path(root) / "data" / "thread.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, text
