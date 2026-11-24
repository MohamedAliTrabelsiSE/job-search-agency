"""Split candidates.json into text-level pass, hold, and fail.

text_pass means the posting's own words offer sponsorship or relocation and
do not contain a block phrase. It does not mean the application form was
opened, and it does not mean anyone may submit.

v0.1 has no browser. There is no flag that submits an application.

Usage:
    py -3 src/gate.py
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Text-level sponsorship gate. Does not open forms.")
    parser.add_argument("--in", dest="src", default=str(ROOT / "data" / "candidates.json"))
    parser.add_argument("--out", default=str(ROOT / "data" / "gated.json"))
    args = parser.parse_args()

    payload = json.loads(Path(args.src).read_text(encoding="utf-8"))
    buckets = {"text_pass": [], "hold": [], "fail": []}
    for job in payload.get("candidates") or []:
        status = job.get("sponsorship")
        if status == "offered":
            buckets["text_pass"].append(job)
        elif status == "blocked":
            buckets["fail"].append(job)
        else:
            buckets["hold"].append(job)

    result = {
        "meaning": {
            "text_pass": "The posting text offers sponsorship or relocation and states no block. The form has not been opened. A person still has to approve any application.",
            "hold": "No clear offer, or the text contradicts itself. Do not apply on this evidence.",
            "fail": "The posting refuses sponsorship or requires an existing right to work.",
        },
        "counts": {k: len(v) for k, v in buckets.items()},
        **buckets,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"text_pass {result['counts']['text_pass']}  hold {result['counts']['hold']}  fail {result['counts']['fail']}")
    print(f"wrote {out}")
    for job in buckets["text_pass"]:
        print(f"  {job['company']}  {job['title'][:56]}  {job['url']}")


if __name__ == "__main__":
    main()
