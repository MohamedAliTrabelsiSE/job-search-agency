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
from eligibility import assess
from matching import compare

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


class RestrictionTest(unittest.TestCase):
    def test_job_restrictions_override_worldwide_marketing(self):
        prefs=dict(PREFS,current_country='Tunisia')
        cases=[
            ('Remote, Global','Hiring only residents of Brazil. We serve customers worldwide.','excluded'),
            ('Remote, North America','Our team operates worldwide.','excluded'),
            ('Remote, Global','This is an in-person role in San Francisco.','excluded'),
            ('Remote, Global','This position is on-site in San Francisco.','excluded'),
            ('Remote, Atlantis','Our team operates worldwide.','needs_verification'),
            ('Remote, Global','Only residents of Atlantis may apply.','needs_verification'),
            ('Remote, LATAM','Our team operates worldwide.','excluded'),
        ]
        for location,text,expected in cases:
            with self.subTest(location=location,text=text):
                result=assess({'location':location,'description':text},prefs,'worldwide')
                self.assertEqual(result['status'],expected)
                self.assertTrue(result['evidence'])

    def test_structured_office_metadata_overrides_remote_marketing(self):
        result=assess({'location':'Remote, Global','workplace_type':'onsite','description':'Work worldwide.'},PREFS,'worldwide')
        self.assertEqual(result['status'],'excluded')


class RequirementsTest(unittest.TestCase):
    def test_preferred_and_alternative_skills_do_not_become_independent_requirements(self):
        for text in ('Required: Python.\nNice to have:\nExperience with Go.',
                     'Required: experience with Go or Python.'):
            with self.subTest(text=text):
                result=compare({'title':'Backend Engineer','description':text},FACTS)
                self.assertEqual(result['decision'],'recommended')
                self.assertEqual(result['missing_required_skills'],[])
        self.assertIn('Go',compare({'title':'Backend Engineer','description':'Required: Python.\nNice to have:\nGo.'},FACTS)['preferred_skills'])

    def test_required_heading_survives_nodejs_and_html_lists(self):
        text='<h2>Requirements</h2><ul><li>Node.js and TypeScript</li></ul><h2>Nice to have</h2><ul><li>Experience with Go</li></ul>'
        result=compare({'title':'Backend Engineer','description':text},FACTS)
        self.assertEqual(set(result['required_skills']),{'Node.js','TypeScript'})
        self.assertNotIn('Go',result['missing_required_skills'])

    def test_core_expertise_missing_blocks_a_python_only_match(self):
        result=compare({'title':'Software Engineer','description':'Required: expert Linux administration, advanced networking and cloud infrastructure. Python.'},FACTS)
        self.assertEqual(result['decision'],'excluded')
        self.assertIn('Linux administration',result['missing_essential_expertise'])
        self.assertTrue(result['decision_reasons'])

    def test_uninterpreted_mandatory_expertise_requires_review(self):
        result=compare({'title':'Software Engineer','description':'Required: Python.\nMust have deep expertise in frobnication.'},FACTS)
        self.assertEqual(result['decision'],'needs_verification')
        self.assertTrue(result['unresolved_requirements'])


if __name__=='__main__':
    unittest.main()
