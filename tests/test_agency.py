import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ats_check import findings, revise
from check_ready import missing
from draft_cv import draft
from load_config import load_json, load_simple_yaml
from merge import merge_cards
from places import scouts_for
from screen import classify_worldwide

FACTS = load_json(ROOT / "config" / "cv_facts.example.json")
PREFS = load_json(ROOT / "config" / "preferences.example.json")
WORLD = load_simple_yaml(ROOT / "config" / "rules.worldwide.yaml")


class AgencyTest(unittest.TestCase):
    def test_missing_profile_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(missing(folder), ["cv_facts.json", "preferences.json"])

    def test_scouts_follow_interest(self):
        self.assertEqual(scouts_for({"interest": "remote", "places": ["Germany"]}), ["worldwide"])
        self.assertEqual(
            scouts_for({"interest": "relocate", "places": ["Germany", "Netherlands", "Sweden"]}),
            ["dach", "benelux-ie", "nordics"],
        )
        both = scouts_for({"interest": "both", "places": ["Germany", "Ireland"]})
        self.assertEqual(both[0], "worldwide")
        self.assertIn("dach", both)
        self.assertIn("benelux-ie", both)

    def test_worldwide_remote_in_one_country_is_blocked(self):
        found = classify_worldwide("Remote - Berlin", "Join our Berlin office.", WORLD)
        self.assertEqual(found["status"], "blocked")
        poland = classify_worldwide("Remote, Poland", "Backend engineer.", WORLD)
        self.assertEqual(poland["status"], "blocked")

    def test_worldwide_anywhere_is_offered(self):
        found = classify_worldwide("Remote", "Work from anywhere in the world.", WORLD)
        self.assertEqual(found["status"], "offered")

    def test_merge_drops_applied_and_keeps_three(self):
        payload = {
            "candidates": [
                {"company": "Kept", "title": "Backend Engineer", "sponsorship": "offered"},
                {"company": "almedia", "title": "Backend Engineer", "sponsorship": "offered"},
                {"company": "Held", "title": "Backend Engineer", "sponsorship": "unknown"},
            ]
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "scout-dach.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            cards = merge_cards([path], {"applied": ["almedia"], "rejected": []}, limit=3)
        self.assertEqual([card["company"] for card in cards], ["Kept"])
        self.assertEqual(cards[0]["path"], "relocation")

    def test_ats_rejects_invented_tool_and_a_visa_on_remote(self):
        card = {"path": "worldwide", "title": "Backend Engineer", "excerpt": "TypeScript APIs"}
        cv = draft(FACTS, PREFS, card)
        cv["experience"][0]["bullets"].append("Operated the platform on Kubernetes.")
        cv["summary"] = "Requires visa sponsorship."
        issues = findings(cv, FACTS, card)
        self.assertTrue(any(item["quote"] == "Kubernetes" for item in issues))
        self.assertTrue(any(item["quote"] == "visa" for item in issues))
        revised = revise(cv, issues)
        self.assertEqual(findings(revised, FACTS, card), [])

    def test_relocation_draft_keeps_the_visa_line(self):
        card = {"path": "relocation", "title": "Backend Engineer", "excerpt": "TypeScript"}
        cv = draft(FACTS, PREFS, card)
        self.assertIn("visa sponsorship", json.dumps(cv).lower())
        self.assertEqual(findings(cv, FACTS, card), [])


if __name__ == "__main__":
    unittest.main()
