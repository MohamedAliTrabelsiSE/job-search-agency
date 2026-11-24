"""Order the pool by overlap with the confirmed resume.

Every card that shares a real word is kept. A card with no shared words is
reported and not drafted. never_add words cannot raise a score.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_ready import ensure_ready
from names import RANKER
from draft_cv import _words
from load_config import load_json
from matching import compare

ROOT = Path(__file__).resolve().parents[1]


def _banned(facts):
    banned = set()
    for skill in facts.get("never_add") or []:
        banned |= _words(skill)
        if skill:
            banned.add(str(skill).lower())
    return banned


def fact_words(facts):
    chunks = [facts.get("headline_default") or ""]
    for row in facts.get("tech") or []:
        if isinstance(row, dict):
            chunks.extend([row.get("label") or "", row.get("items") or ""])
        elif isinstance(row, (list, tuple)):
            chunks.extend(str(part) for part in row)
    for job in facts.get("experience") or []:
        chunks.extend([job.get("title") or "", job.get("stack") or ""])
        chunks.extend(job.get("bullets") or [])
    for proj in facts.get("projects") or []:
        chunks.extend([proj.get("name") or "", proj.get("tagline") or "", proj.get("stack") or ""])
        chunks.extend(proj.get("bullets") or [])
    words = set()
    for chunk in chunks:
        words |= _words(chunk)
    return words - _banned(facts)


def _date_key(published):
    text = published or ""
    if not text:
        return (0,)
    return tuple(-ord(ch) for ch in text)


def rank_cards(cards, facts, policy=None):
    kept = []
    skipped = []
    for card in cards:
        scored = dict(card)
        scored.update(compare(card, facts, policy))
        if scored['decision'] != 'excluded':
            kept.append(scored)
        else:
            skipped.append(scored)
    order = {'recommended':0, 'stretch':1, 'needs_verification':2}
    kept.sort(key=lambda card: (order[card['decision']], -card["score"], _date_key(card.get("published")), (card.get("company") or "").lower()))
    return kept, skipped


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Rank the pool from one search run.')
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    ensure_ready(ROOT)
    data = ROOT / "data"
    pool_path = args.run_dir / "pool.json"
    if not pool_path.exists():
        sys.stderr.write("data/pool.json is missing. Run merge.py first.\n")
        return 2
    pool = load_json(pool_path)
    facts = load_json(data / "cv_facts.json")
    kept, skipped = rank_cards(pool.get("cards") or [], facts)
    out = args.run_dir / "shortlist.json"
    payload = {"count": len(kept), "cards": kept, "skipped": skipped}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{RANKER}  shortlist {len(kept)}")
    for card in kept:
        print(f"  {card['score']:3}  {card['company']}  {card['why']}")
    if skipped:
        print(f"skipped {len(skipped)}")
        for card in skipped:
            print(f"  {card['company']}  {card['why']}")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
