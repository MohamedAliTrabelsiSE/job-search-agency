"""Stop the morning run until a person has finished the first-run interview.

A clone has no resume and no interest on disk. Every entry point calls
ensure_ready before it fetches a job or reads mail.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("cv_facts.json", "preferences.json")

INTERVIEW = """
This agency has no profile yet. Ask the person, then save the answers under data/. Do not search first.

1. General resume. Ask them to drop a PDF or text file, or to paste it. Read only what is written. Save data/cv_facts.json with contact, education, each role, the bullets that already exist, languages, activities, and never_add (tools the resume does not claim). Show that reading back and wait for a correction before saving.

2. Interest. Ask which they want: full remote from where they already live, relocate, or both. If they relocate, ask which places. More than one place is a normal answer.

3. Work right, in their words. For relocation, whether they need a visa. For full remote, that they will keep working from their current country. Save all of this in data/preferences.json.

Both files are gitignored. Do not commit them.
""".strip()


def missing(root=None):
    folder = Path(root or ROOT) / "data"
    return [name for name in REQUIRED if not (folder / name).exists()]


def ensure_ready(root=None):
    absent = missing(root)
    if not absent:
        return
    sys.stderr.write("Missing " + ", ".join(absent) + ".\n" + INTERVIEW + "\n")
    raise SystemExit(2)
