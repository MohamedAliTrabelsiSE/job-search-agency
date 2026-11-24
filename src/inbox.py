"""Read the inbox and record rejections. Never sends.

Runs only when a credential file exists. Without one, the morning run
continues with the scouts alone.

The file is two lines, address then app password, same as a Gmail app
password. The default path is ~/.dsh/smtp.txt. Override with --creds.
The password is never printed.
"""

import argparse
import email
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_ready import ensure_ready
from names import INBOX

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CREDS = Path(os.path.expanduser("~")) / ".dsh" / "smtp.txt"

REJECT = re.compile(
    r"(not moving forward|will not be moving|won't be taking|unsuccessful|rejected|another candidate|not be taking your application)",
    re.I,
)
ACK = re.compile(
    r"(received your (application|resum)|thank you for applying|application was successfully|we've received|we have received)",
    re.I,
)
NOISE = re.compile(r"(newsletter|digest|marketing|verification code|security alert|password)", re.I)


def decode_header_value(value):
    if not value:
        return ""
    parts = []
    for part, enc in decode_header(value):
        if isinstance(part, bytes):
            parts.append(part.decode(enc or "utf-8", "replace"))
        else:
            parts.append(part)
    return " ".join("".join(parts).split())


def company_of(frm, subject):
    display = frm.split("<", 1)[0].strip().strip('"')
    display = re.sub(r"\s+(team|hiring|recruitment|careers)$", "", display, flags=re.I).strip()
    if display and "@" not in display and "no-reply" not in display.lower() and "noreply" not in display.lower():
        return display
    match = re.search(r"application (?:to|at) ([A-Za-z][\w.&' -]{1,40})", subject, re.I)
    return match.group(1).strip() if match else ""


def classify(frm, subject, body):
    blob = f"{subject}\n{body[:2000]}"
    if NOISE.search(blob) and not REJECT.search(blob) and not ACK.search(blob):
        return "other"
    if REJECT.search(blob):
        return "rejection"
    if ACK.search(blob):
        return "acknowledgement"
    low = frm.lower()
    if "no-reply" in low or "noreply" in low or "mailer-daemon" in low:
        return "other"
    return "question"


def load_creds(path):
    lines = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    if len(lines) < 2:
        raise SystemExit("Credential file needs an address and an app password.")
    return lines[0], lines[1].replace(" ", "")


def body_text(msg):
    chunks = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True) or b""
                chunks.append(payload.decode(part.get_content_charset() or "utf-8", "replace"))
    else:
        payload = msg.get_payload(decode=True) or b""
        chunks.append(payload.decode(msg.get_content_charset() or "utf-8", "replace"))
    return "\n".join(chunks)


def remember_rejection(roles_path, company):
    if not company:
        return
    roles = {"applied": [], "rejected": []}
    if roles_path.exists():
        roles.update(json.loads(roles_path.read_text(encoding="utf-8")))
    rejected = {item.lower() for item in roles.get("rejected") or []}
    if company.lower() not in rejected:
        roles.setdefault("rejected", []).append(company)
        roles_path.write_text(json.dumps(roles, ensure_ascii=False, indent=2), encoding="utf-8")


def record_skip(out, reason):
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"count": 0, "messages": [], "skipped": reason}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Classify the inbox. Does not send.")
    parser.add_argument("--creds", default=str(DEFAULT_CREDS))
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--out", default=str(ROOT / "data" / "inbox.json"))
    args = parser.parse_args()
    ensure_ready(ROOT)
    creds = Path(args.creds)
    if not creds.exists():
        print(f"{INBOX} skipped: no credential file")
        record_skip(args.out, "no credential file")
        return 0

    address, password = load_creds(creds)
    since = (datetime.now() - timedelta(days=args.days)).strftime("%d-%b-%Y")
    try:
        mailbox = imaplib.IMAP4_SSL("imap.gmail.com", timeout=20)
        mailbox.login(address, password)
    except (OSError, imaplib.IMAP4.error) as exc:
        print(f"{INBOX} skipped: {exc}")
        record_skip(args.out, "could not connect")
        return 0
    mailbox.select("INBOX")
    _, data = mailbox.search(None, f"(SINCE {since})")
    rows = []
    for num in data[0].split():
        _, fetched = mailbox.fetch(num, "(RFC822)")
        if not fetched or not fetched[0]:
            continue
        msg = email.message_from_bytes(fetched[0][1])
        frm = decode_header_value(msg.get("From"))
        subject = decode_header_value(msg.get("Subject"))
        kind = classify(frm, subject, body_text(msg))
        company = company_of(frm, subject)
        rows.append({
            "from": frm[:80],
            "subject": subject[:120],
            "date": decode_header_value(msg.get("Date"))[:40],
            "kind": kind,
            "company": company,
        })
        if kind == "rejection":
            remember_rejection(ROOT / "data" / "roles.json", company)
    mailbox.logout()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"count": len(rows), "messages": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {}
    for row in rows:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
    print(f"{INBOX}  {len(rows)} {counts}")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
