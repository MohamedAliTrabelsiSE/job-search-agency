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
    def test_posting_age_and_unknown_date_do_not_mean_closed(self):
        today=datetime.date(2026,11,25)
        for published in ('2026-01-01',''):
            job={'platform':'ashby','company':'fictional','title':'Backend Engineer','location':'Remote, Global',
                 'published':published,'url':'https://example.com/job','description':'Required: Python.'}
            self.assertTrue(keep(job,RULES,today=today))
            result=discover({'ashby':['fictional']},RULES,PREFS,board_reader=lambda *a:[job])
            self.assertEqual(result['count'],1)
            self.assertIn(result['candidates'][0]['freshness']['status'],('older','unknown'))
            self.assertEqual(result['candidates'][0]['availability']['status'],'observed_listed')
        recent_only=dict(RULES,freshness_mode='recent_only')
        self.assertFalse(keep(dict(job,published='2026-01-01'),recent_only,today=today))
        self.assertTrue(keep(dict(job,published=''),recent_only,today=today))
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
            ('Remote, Global','Applicants must be authorized to work in Brazil. Worldwide customers.','excluded'),
        ]
        for location,text,expected in cases:
            with self.subTest(location=location,text=text):
                result=assess({'location':location,'description':text},prefs,'worldwide')
                self.assertEqual(result['status'],expected)
                self.assertTrue(result['evidence'])

    def test_structured_office_metadata_overrides_remote_marketing(self):
        result=assess({'location':'Remote, Global','workplace_type':'onsite','description':'Work worldwide.'},PREFS,'worldwide')
        self.assertEqual(result['status'],'excluded')

    def test_south_america_is_not_latam_membership(self):
        result=assess({'location':'Remote, South America','description':'We work worldwide.'},dict(PREFS,current_country='Mexico'),'worldwide')
        self.assertEqual(result['status'],'excluded')


class RequirementsTest(unittest.TestCase):
    def test_required_skills_heading_and_comma_separated_alternatives(self):
        result=compare({'title':'Software Engineer','description':'Required skills and experience\nPython\nKnowledge of Linux\nNice to have\nGo'},FACTS)
        self.assertEqual(result['decision'],'excluded')
        self.assertIn('Linux',result['missing_essential_expertise'])
        result=compare({'title':'Software Engineer','description':'Requirements:\nExperience with Rust, Go, Python, Flutter or C/C++.'},FACTS)
        self.assertEqual(result['decision'],'recommended')
        self.assertEqual(result['missing_required_skills'],[])
        self.assertTrue(result['one_of_requirements'][0]['satisfied'])

    def test_explicit_optional_wording_overrides_inferred_title_skill(self):
        result=compare({'title':'Software Engineer - Python/Golang - Kubernetes','description':'Go or Python is required.\nKubernetes experience is preferred but not strictly required.'},FACTS)
        self.assertNotIn('Kubernetes',result['required_skills'])
        self.assertEqual(result['decision'],'recommended')
    def test_experience_stretch_is_bounded_and_penalized(self):
        facts=dict(FACTS,years_experience=2)
        outcomes=[]
        for years,expected in ((2,'recommended'),(3,'stretch'),(5,'excluded'),(8,'excluded'),(20,'excluded')):
            with self.subTest(years=years):
                result=compare({'title':'Backend Engineer','description':f'Required: Python. {years} years of experience.'},facts)
                self.assertEqual(result['decision'],expected)
                outcomes.append(result)
        self.assertGreater(outcomes[0]['score'],outcomes[1]['score'])
        self.assertIn('experience',outcomes[-1]['decision_reasons'][0].lower())

    def test_optional_years_do_not_become_a_minimum(self):
        result=compare({'title':'Backend Engineer','description':'Required: Python.\nNice to have:\n20 years of experience.'},dict(FACTS,years_experience=2))
        self.assertEqual(result['decision'],'recommended')
        self.assertIsNone(result['experience_requirement_years'])
    def test_preferred_and_alternative_skills_do_not_become_independent_requirements(self):
        for text in ('Required: Python.\nNice to have:\nExperience with Go.',
                     'Required: experience with Go or Python.'):
            with self.subTest(text=text):
                result=compare({'title':'Backend Engineer','description':text},FACTS)
                self.assertEqual(result['decision'],'recommended')
                self.assertEqual(result['missing_required_skills'],[])
        self.assertIn('Go',compare({'title':'Backend Engineer','description':'Required: Python.\nNice to have:\nGo.'},FACTS)['preferred_skills'])

    def test_one_of_and_parenthesized_groups_do_not_swallow_other_requirements(self):
        result=compare({'title':'Backend Engineer','description':'Required: one of Go, Python.'},FACTS)
        self.assertEqual(result['decision'],'recommended')
        result=compare({'title':'Backend Engineer','description':'Required: TypeScript, Node.js, (Go or Python).'},FACTS)
        self.assertEqual(set(result['required_skills']),{'TypeScript','Node.js'})
        self.assertEqual(result['decision'],'recommended')

    def test_essential_alternatives_and_cardinality_do_not_become_minor_stretches(self):
        result=compare({'title':'Software Engineer','description':'Required: Python.\nExpertise in Linux administration or networking.'},FACTS)
        self.assertEqual(result['decision'],'excluded')
        result=compare({'title':'Software Engineer','description':'Required: Python.\nExperience with two or more of Linux, distributed systems, container images.'},FACTS)
        self.assertEqual(result['decision'],'needs_verification')

    def test_required_heading_survives_nodejs_and_html_lists(self):
        text='<h2>Requirements</h2><ul><li>Node.js and TypeScript</li></ul><h2>Nice to have</h2><ul><li>Experience with Go</li></ul>'
        result=compare({'title':'Backend Engineer','description':text},FACTS)
        self.assertEqual(set(result['required_skills']),{'Node.js','TypeScript'})
        self.assertNotIn('Go',result['missing_required_skills'])

    def test_flattened_headers_and_parenthetical_preference_keep_linux_required(self):
        text='What we are looking for in you TypeScript skills. Experience with Linux (Debian or Ubuntu preferred). Nice-to-have skills Experience with Go. What we offer colleagues Worldwide team.'
        result=compare({'title':'Web Engineer - JS, TS','description':text},FACTS)
        self.assertIn('Linux',result['missing_essential_expertise'])
        self.assertIn('Go',result['preferred_skills'])
        self.assertNotIn('Go',result['missing_required_skills'])
        self.assertEqual(result['decision'],'excluded')

    def test_core_expertise_missing_blocks_a_python_only_match(self):
        result=compare({'title':'Software Engineer','description':'Required: expert Linux administration, advanced networking and cloud infrastructure. Python.'},FACTS)
        self.assertEqual(result['decision'],'excluded')
        self.assertIn('Linux administration',result['missing_essential_expertise'])
        self.assertTrue(result['decision_reasons'])

    def test_specialist_domain_and_deep_technology_requirements_are_not_ignored(self):
        result=compare({'title':'Backend Engineer','description':'Requirements:\nYou are deeply familiar with TypeScript and GraphQL.\nYou have an understanding of the blockchain industry.'},FACTS)
        self.assertEqual(result['decision'],'excluded')
        self.assertIn('Blockchain',result['missing_essential_expertise'])
        self.assertIn('GraphQL',result['missing_essential_expertise'])

    def test_who_you_are_section_retains_required_operating_system_evidence(self):
        result=compare({'title':'Software Engineer','description':'Who you are\nProfessional proficiency in Python.\nYou are comfortable with Ubuntu as a deployment platform.\nAbout the company\nWe use Go.'},FACTS)
        self.assertEqual(result['decision'],'excluded')
        self.assertIn('Linux',result['missing_essential_expertise'])

    def test_technology_overlap_without_understood_requirements_is_not_recommended(self):
        result=compare({'title':'Software Engineer','description':'We use Python.'},FACTS)
        self.assertEqual(result['decision'],'needs_verification')

    def test_uninterpreted_mandatory_expertise_requires_review(self):
        result=compare({'title':'Software Engineer','description':'Required: Python.\nMust have deep expertise in frobnication.'},FACTS)
        self.assertEqual(result['decision'],'needs_verification')
        self.assertTrue(result['unresolved_requirements'])

    def test_unknown_essential_platform_cannot_be_masked_by_python(self):
        result=compare({'title':'Software Engineer','description':'Requirements:\nStrong Python.\nExperience deploying OpenStack services.'},FACTS)
        self.assertEqual(result['decision'],'needs_verification')
        self.assertTrue(result['unresolved_requirements'])


if __name__=='__main__':
    unittest.main()
