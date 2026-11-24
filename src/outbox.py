"""Write a draft into outbox/. This file has no network code.

Usage:
    py -3 src/outbox.py --kind reply --to ada@example.com --subject "Hello" --body examples/sample-jd.md
"""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Save a draft. Never sends it.")
    parser.add_argument("--kind", choices=("reply", "application-note"), default="reply")
    parser.add_argument("--to", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True, help="Path to a text file, or a literal starting with @ is not used; pass a file path")
    args = parser.parse_args()

    body = Path(args.body).read_text(encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", args.subject.lower()).strip("-")[:40] or "draft"
    dest = ROOT / "outbox" / f"{stamp}-{args.kind}-{slug}.md"
    dest.write_text(
        "\n".join([
            f"kind: {args.kind}",
            f"to: {args.to}",
            f"subject: {args.subject}",
            "status: draft",
            "sent: no",
            "",
            body,
            "",
        ]),
        encoding="utf-8",
    )
    print(f"draft {dest}")
    print("not sent")


if __name__ == "__main__":
    main()
