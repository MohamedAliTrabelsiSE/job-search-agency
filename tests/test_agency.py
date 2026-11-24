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
from rank import rank_cards
from thread import build_thread
from names import speak
from preview_cv import build_preview
from render_cv import normalize, page_is_locked, refuse_other_layout, to_text
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

    def test_rank_prefers_the_resume_match_over_file_order(self):
        benelux = {
            "candidates": [{
                "company": "salesco",
                "title": "Account Executive",
                "sponsorship": "offered",
                "excerpt": "Quota and a short backend note.",
                "published": "2026-11-20",
            }]
        }
        worldwide = {
            "candidates": [{
                "company": "apico",
                "title": "Backend Engineer",
                "sponsorship": "offered",
                "excerpt": "TypeScript and Node.js REST APIs.",
                "published": "2026-11-01",
            }]
        }
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "scout-benelux-ie.json"
            second = Path(folder) / "scout-worldwide.json"
            first.write_text(json.dumps(benelux), encoding="utf-8")
            second.write_text(json.dumps(worldwide), encoding="utf-8")
            cards = merge_cards([first, second], {}, limit=None)
        kept, _skipped = rank_cards(cards, FACTS)
        self.assertEqual(kept[0]["company"], "apico")
        self.assertGreater(kept[0]["score"], kept[1]["score"])

    def test_rank_ignores_never_add_and_keeps_every_match(self):
        cards = [
            {"company": "kco", "title": "Platform", "excerpt": "Kubernetes only", "published": "2026-11-20", "sponsorship": "offered"},
            {"company": "real", "title": "API", "excerpt": "TypeScript", "published": "2026-01-01", "sponsorship": "offered"},
            {"company": "node", "title": "API", "excerpt": "TypeScript Node.js", "published": "2026-02-01", "sponsorship": "offered"},
            {"company": "rest", "title": "API", "excerpt": "TypeScript REST APIs", "published": "2026-03-01", "sponsorship": "offered"},
            {"company": "full", "title": "API", "excerpt": "TypeScript Node.js REST APIs", "published": "2026-04-01", "sponsorship": "offered"},
            {"company": "sales", "title": "Account Executive", "excerpt": "Quota and pipeline", "published": "2026-11-20", "sponsorship": "offered"},
        ]
        kept, skipped = rank_cards(cards, FACTS)
        self.assertEqual([card["company"] for card in kept], ["full", "rest", "node", "real"])
        self.assertEqual([card["company"] for card in skipped], ["kco", "sales"])
        self.assertNotIn("kubernetes", kept[0]["why"])
        self.assertEqual(skipped[0]["why"], "no overlap with your resume")

    def test_draft_keeps_the_persons_headline_and_skips_empty_activities(self):
        card = {"path": "worldwide", "title": "Staff Kubernetes Engineer", "excerpt": "Go and Kubernetes"}
        cv = draft(FACTS, PREFS, card)
        first_bullet = FACTS["experience"][0]["bullets"][0]
        self.assertEqual(cv["headline"], FACTS["headline_default"])
        self.assertNotIn(first_bullet, cv["summary"])
        self.assertNotIn("remotely", json.dumps(cv["contact"]).lower())
        self.assertIn("remotely", cv["work_right"].lower())
        text = to_text(normalize(cv))
        self.assertNotIn("Activities", text)
        self.assertNotIn("Stack:", text)
        self.assertLess(text.index("EXPERIENCE"), text.index("PROJECTS"))
        self.assertLess(text.index("PROJECTS"), text.index("EDUCATION"))
        self.assertLess(text.index("EDUCATION"), text.index("SKILLS"))
        self.assertLess(text.index("SKILLS"), text.index("LANGUAGES"))

    def test_overview_is_not_a_pasted_bullet_and_the_page_stays_locked(self):
        card = {"path": "worldwide", "title": "Backend Engineer", "excerpt": "TypeScript Node.js REST APIs"}
        cv = draft(FACTS, PREFS, card)
        first_bullet = FACTS["experience"][0]["bullets"][0]
        self.assertNotIn(first_bullet, cv["summary"])
        self.assertIn(FACTS["experience"][0]["company"], cv["summary"])
        self.assertIn(FACTS["projects"][0]["name"], cv["summary"])
        self.assertLess(cv["summary"].index(FACTS["projects"][0]["name"]), cv["summary"].lower().index("remotely"))
        self.assertIn(PREFS["work_right"]["remote"], cv["summary"])
        self.assertNotIn("visa", cv["summary"].lower())
        text = to_text(normalize(cv))
        self.assertLess(text.index("PROFESSIONAL OVERVIEW"), text.index("WORK EXPERIENCE"))
        self.assertLess(text.index("WORK EXPERIENCE"), text.index("PROJECTS"))
        self.assertLess(text.index("PROJECTS"), text.index("EDUCATION"))
        self.assertLess(text.index("EDUCATION"), text.index("SKILLS"))
        self.assertLess(text.index("SKILLS"), text.index("LANGUAGES"))
        skills = text.split("SKILLS", 1)[1].split("LANGUAGES", 1)[0]
        self.assertLess(skills.index("TypeScript"), skills.index("Python"))
        self.assertNotIn("Languages:", text)
        self.assertTrue(page_is_locked({}))
        self.assertTrue(page_is_locked({"interest": "both"}))
        self.assertFalse(page_is_locked({"template_override": "two columns"}))
        cv["layout"] = "two-column"
        with self.assertRaises(ValueError):
            refuse_other_layout(cv, {})
        refuse_other_layout(cv, {"template_override": "two columns"})

    def test_draft_keeps_every_project_and_bullet(self):
        facts = json.loads(json.dumps(FACTS))
        facts["projects"] = [
            {"name": f"Project {i}", "bullets": [f"Shipped part {i} in TypeScript."], "stack": "TypeScript"}
            for i in range(5)
        ]
        facts["experience"][0]["bullets"] = [f"Shipped change {i} in TypeScript." for i in range(6)]
        cv = draft(facts, PREFS, {"path": "worldwide", "title": "Backend Engineer", "excerpt": "TypeScript"})
        self.assertEqual(len(cv["projects"]), 5)
        self.assertEqual(len(cv["experience"][0]["bullets"]), 6)
        preview = build_preview(facts, PREFS)
        self.assertEqual(len(preview["projects"]), 5)
        self.assertIn("Project 0", preview["summary"])
        self.assertIn("Project 4", preview["summary"])

    def test_progress_lines_name_the_speaker(self):
        self.assertEqual(speak("Remy", "boards 12  errors 0  candidates 3  {}"), "Remy  boards 12  errors 0  candidates 3  {}")
        self.assertEqual(speak("Sami", "pool 8"), "Sami  pool 8")
        self.assertEqual(speak("", "pool 0"), "pool 0")

    def test_thread_shows_one_reply_from_marco_to_maya(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / "data"
            data.mkdir()
            (data / "preferences.json").write_text(
                json.dumps({"interest": "both", "places": ["Germany"]}),
                encoding="utf-8",
            )
            (data / "inbox.json").write_text(
                json.dumps({"count": 0, "messages": [], "skipped": "no credential file"}),
                encoding="utf-8",
            )
            (data / "scout-worldwide.json").write_text(
                json.dumps({"candidates": [{"sponsorship": "blocked"}, {"sponsorship": "offered"}]}),
                encoding="utf-8",
            )
            (data / "scout-dach.json").write_text(
                json.dumps({"candidates": [{"sponsorship": "offered"}]}),
                encoding="utf-8",
            )
            (data / "shortlist.json").write_text(
                json.dumps({
                    "cards": [{"company": "apico", "title": "Backend Engineer"}],
                    "skipped": [{"company": "salesco"}],
                }),
                encoding="utf-8",
            )
            text = build_thread(root, [{
                "company": "apico",
                "title": "Backend Engineer",
                "findings": [{"quote": "visa"}],
                "remaining": [],
            }])
        self.assertIn("Ida → Sami    Mail was not connected. Nothing sent.", text)
        self.assertIn("Remy → Sami    2 jobs, 1 passed the text check.", text)
        self.assertIn("Nico → Sami    1 job, 1 passed the text check.", text)
        self.assertNotIn("Lina →", text)
        self.assertIn("Theo → Maya    1 job, best first. 1 skipped, no overlap.", text)
        self.assertIn("Maya → Marco    resume for Backend Engineer at apico.", text)
        self.assertIn("Marco → Maya    visa. Maya fixed that once.", text)
        self.assertIn("Sami → you    1 folder. Nothing submitted and nothing sent.", text)
        self.assertEqual(text.count("Marco → Maya"), 1)


if __name__ == "__main__":
    unittest.main()
