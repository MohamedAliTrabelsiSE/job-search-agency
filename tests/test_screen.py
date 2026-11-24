import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from load_config import load_simple_yaml
from screen import classify_sponsorship, seniority_blocked, title_ok, within_cutoff

ROOT = Path(__file__).resolve().parents[1]
RULES = load_simple_yaml(ROOT / "config" / "rules.example.yaml")


class ScreenTest(unittest.TestCase):
    def test_block_phrase_is_not_an_offer(self):
        text = "We are unable to offer visa sponsorship for this role."
        found = classify_sponsorship(text, RULES)
        self.assertEqual(found["status"], "blocked")
        self.assertEqual(found["offers"], [])

    def test_plain_offer(self):
        text = "Perks: relocation support and visa support."
        found = classify_sponsorship(text, RULES)
        self.assertEqual(found["status"], "offered")
        self.assertIn("visa support", found["offers"])

    def test_conflict_when_both_appear(self):
        text = "Visa support is available. Some offices do not sponsor and say no visa sponsorship."
        found = classify_sponsorship(text, RULES)
        self.assertEqual(found["status"], "conflict")

    def test_senior_title_blocked_and_backend_allowed(self):
        self.assertTrue(seniority_blocked("Senior Backend Engineer", RULES))
        self.assertTrue(title_ok("Product Engineer", RULES))
        self.assertFalse(title_ok("Account Executive", RULES))

    def test_cutoff(self):
        today = datetime.date(2026, 11, 24)
        self.assertTrue(within_cutoff("2026-11-16", RULES, today=today))
        self.assertFalse(within_cutoff("2026-10-01", RULES, today=today))

    def test_yaml_lists(self):
        sources = load_simple_yaml(ROOT / "config" / "sources.example.yaml")
        self.assertIn("augustus", sources["ashby"])
        self.assertEqual(sources["lever"], [])


if __name__ == "__main__":
    unittest.main()
