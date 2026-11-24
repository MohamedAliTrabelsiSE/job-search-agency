"""Suitability regressions reported during manual acceptance."""
import copy
import datetime
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from discover import discover, keep
from load_config import load_json, load_simple_yaml
from screen import title_ok, seniority_blocked

FACTS = load_json(ROOT/'config/cv_facts.example.json')
PREFS = load_json(ROOT/'config/preferences.example.json')
RULES = load_simple_yaml(ROOT/'config/rules.worldwide.yaml')


class EvidenceTest(unittest.TestCase):
    def test_plausible_titles_and_internal_tools_survive(self):
        for title in ('Web Engineer - JS, TS, Flutter','Node.js Developer','JavaScript Developer','Backend Engineer, Internal Tools'):
            with self.subTest(title=title):
                self.assertTrue(title_ok(title,RULES))
                self.assertFalse(seniority_blocked(title,RULES))
        self.assertTrue(seniority_blocked('Software Engineering Intern',RULES))
        self.assertTrue(seniority_blocked('Backend Developer Internship',RULES))

    def test_emea_full_ad_and_paragraph_structure_reach_assessment(self):
        description='Required:\nNode.js and TypeScript\n\nNice to have:\nExperience with Go.'
        job={'platform':'ashby','company':'fictional','title':'Node.js Developer','location':'EMEA',
             'published':datetime.date.today().isoformat(),'url':'https://example.com/job','is_remote':True,
             'description':description+'\nWork from anywhere in the world.'}
        result=discover({'ashby':['fictional']},RULES,PREFS,board_reader=lambda *a:[job])
        self.assertEqual(result['count'],1)
        card=result['candidates'][0]
        self.assertIn('Nice to have:\nExperience with Go.',card['description'])
        self.assertEqual(card['description_raw'],job['description'])
        self.assertEqual(card['eligibility']['status'],'eligible')


if __name__=='__main__':
    unittest.main()
