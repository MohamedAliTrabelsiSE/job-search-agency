"""Render the locked layout from the confirmed facts, before any search.

The original file the person gave is the source of the facts. This preview
is the resume they see.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_ready import ensure_ready
from draft_cv import draft
from load_config import load_json
from render_cv import render_files

ROOT = Path(__file__).resolve().parents[1]


def build_preview(facts, preferences):
    card = {"path": "worldwide", "title": "", "excerpt": ""}
    return draft(facts, preferences, card)


def main():
    ensure_ready(ROOT)
    facts = load_json(ROOT / "data" / "cv_facts.json")
    preferences = load_json(ROOT / "data" / "preferences.json")
    folder = ROOT / "outbox" / "preview"
    docx_path, text_path = render_files(build_preview(facts, preferences), folder, preferences)
    print(docx_path)
    print(text_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
