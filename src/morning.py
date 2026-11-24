"""One morning wave. Stops before any application or email is sent.

Order: inbox clerk (if credentials exist), the scouts for this interest,
merger, ranker, then one resume per matching job. The writer pass is
src/draft_cv.py. The ATS pass is src/ats_check.py, with one revision.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ats_check import findings, revise
from check_ready import ensure_ready
from draft_cv import draft
from load_config import load_json
from render_cv import render_files

ROOT = Path(__file__).resolve().parents[1]


def _run(script):
    return subprocess.run([sys.executable, str(ROOT / "src" / script)]).returncode


def slug(text):
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:48] or "role"


def main():
    ensure_ready(ROOT)
    if _run("inbox.py") not in (0, None):
        return 1
    if _run("scout.py") not in (0, None):
        return 1
    if _run("merge.py") not in (0, None):
        return 1
    if _run("rank.py") not in (0, None):
        return 1

    shortlist = load_json(ROOT / "data" / "shortlist.json")
    facts = load_json(ROOT / "data" / "cv_facts.json")
    preferences = load_json(ROOT / "data" / "preferences.json")
    cards = shortlist.get("cards") or []
    if not cards:
        print("No card passed the gate. Nothing was drafted, sent, or submitted.")
        return 0

    for card in cards:
        folder = ROOT / "outbox" / f"{slug(card['company'])}-{slug(card['title'])}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
        cv = draft(facts, preferences, card)
        issues = findings(cv, facts, card)
        if issues:
            cv = revise(cv, issues)
            issues = findings(cv, facts, card)
        (folder / "cv.json").write_text(json.dumps(cv, ensure_ascii=False, indent=2), encoding="utf-8")
        (folder / "ats.json").write_text(
            json.dumps({"verdict": "pass" if not issues else "block", "findings": issues}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if issues:
            print(f"blocked {card['company']} {card['title'][:40]}")
            continue
        render_files(cv, folder)
        print(f"ready {card.get('score', '')} {card.get('why', '')} {folder}")

    print("Stopped. Nothing was submitted and nothing was sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
