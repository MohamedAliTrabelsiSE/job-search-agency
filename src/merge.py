"""One card per company, after every scout and the inbox clerk have finished.

Keeps text-pass roles only. Drops a company that was already applied to or
that already sent a rejection. The ranker, not this step, decides order.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_ready import ensure_ready
from load_config import load_json

ROOT = Path(__file__).resolve().parents[1]


def blocked_companies(roles):
    names = []
    for key in ("applied", "rejected", "skipped"):
        names.extend(roles.get(key) or [])
    return {str(name).lower() for name in names}


def merge_cards(scout_files, roles, limit=None):
    blocked = blocked_companies(roles or {})
    seen = set()
    cards = []
    for path in scout_files:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        region = Path(path).stem.replace("scout-", "")
        path_kind = "worldwide" if region == "worldwide" else "relocation"
        for job in payload.get("candidates") or []:
            if job.get("sponsorship") != "offered":
                continue
            company = (job.get("company") or "").lower()
            if not company or company in seen or company in blocked:
                continue
            seen.add(company)
            card = dict(job)
            card["path"] = path_kind
            card["scout"] = region
            cards.append(card)
            if limit is not None and len(cards) >= limit:
                return cards
    return cards


def main():
    ensure_ready(ROOT)
    data = ROOT / "data"
    files = sorted(data.glob("scout-*.json"))
    roles_path = data / "roles.json"
    roles = load_json(roles_path) if roles_path.exists() else {}
    cards = merge_cards(files, roles)
    out = data / "pool.json"
    out.write_text(json.dumps({"count": len(cards), "cards": cards}, ensure_ascii=False, indent=2), encoding="utf-8")
    from names import LEAD, speak

    print(speak(LEAD, f"pool {len(cards)}"))
    for card in cards:
        print(f"  {card['path']:12} {card['company']}  {card['title'][:48]}")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
