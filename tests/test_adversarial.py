"""Adversarial regressions: fictional inputs, real interfaces, no network."""
import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from eligibility import assess
from matching import compare
from morning import run_workflow
from profile import confirm

FACTS=json.loads((ROOT/'config/cv_facts.example.json').read_text(encoding='utf-8'))
FACTS['years_experience']=3
PREFS=json.loads((ROOT/'config/preferences.example.json').read_text(encoding='utf-8'))
PREFS.update(current_country='Tunisia',interest='remote',places=[])
PREFS['work_right']['remote']='Working remotely from Tunisia.'


class AdversarialTest(unittest.TestCase):
    def eligibility(self,text,prefs=PREFS):
        return assess({'location':'Remote, Global','description':text},prefs,'worldwide')['status']

    def fit(self,text,facts=FACTS):
        return compare({'title':'Backend Engineer','description':text},facts)

    def test_country_exception_excludes_candidate(self):
        self.assertEqual(self.eligibility('Work from anywhere except Tunisia.'),'excluded')

    def test_region_exception_excludes_member(self):
        self.assertEqual(self.eligibility('Worldwide remote, excluding North America.',dict(PREFS,current_country='Canada')),'excluded')

    def test_exceptions_do_not_become_allowed_scopes(self):
        for text,expected in (
            ('Worldwide remote, excluding North America.','eligible'),
            ('Worldwide remote, excluding Atlantis.','needs_verification'),
            ('Worldwide remote, except Germany, but applicants in Tunisia are welcome.','eligible'),
            ('Remote from Europe except Germany.','excluded'),
        ):
            with self.subTest(text=text):
                self.assertEqual(self.eligibility(text),expected)
        self.assertEqual(assess({'location':'Remote, Global except Tunisia','description':'Required: Python.'},PREFS,'worldwide')['status'],'excluded')

    def test_exclusion_membership_and_explicit_denials(self):
        for country,expected in (('Germany','excluded'),('France','eligible')):
            result=assess({'location':'Remote, Europe except Germany','description':'Fully remote work.'},dict(PREFS,current_country=country),'worldwide')
            self.assertEqual(result['status'],expected)
        for text in (
            'This remote role is not available in Tunisia.',
            'We cannot hire in Tunisia. Work worldwide.',
            'We do not hire in Tunisia. Work worldwide.',
            'Remote applicants must not be based in Tunisia.',
            'Worldwide remote, excluding Germany and North America, except Tunisia.',
        ):
            with self.subTest(text=text):
                self.assertEqual(self.eligibility(text),'excluded')

    def test_country_restriction_is_not_broadened_by_region_label(self):
        result=assess({'location':'Remote, Germany, Europe','description':'Work worldwide.'},dict(PREFS,current_country='France'),'worldwide')
        self.assertEqual(result['status'],'excluded')

    def test_negated_attendance_is_not_required_attendance(self):
        self.assertEqual(self.eligibility('This is not an in-person role. Work worldwide.'),'eligible')

    def test_attendance_denials_do_not_hide_independent_requirements(self):
        for text,expected in (
            ('No office attendance required. Work worldwide.','eligible'),
            ('In-person work is not required. Work worldwide.','eligible'),
            ('No visa sponsorship, this is an in-person role. Work worldwide.','excluded'),
            ('No relocation support and this is an in-person role. Work worldwide.','excluded'),
            ('This is an in-person role with no relocation support. Work worldwide.','excluded'),
            ('This is not an in-person role, but office attendance required twice a week.','excluded'),
        ):
            with self.subTest(text=text):
                self.assertEqual(self.eligibility(text),expected)

    def test_company_headquarters_do_not_restrict_job_location(self):
        self.assertEqual(self.eligibility('We are based in Germany. You can work from anywhere in the world.'),'eligible')

    def test_company_location_cannot_hide_candidate_location(self):
        for text in (
            'We are based in Germany and applicants must be based in Brazil. Work worldwide.',
            'We are based in Germany, but applicants must be based in Brazil. Work worldwide.',
            'Our company is based in Germany. Candidates must be located in Brazil. Work worldwide.',
            'Candidates must be based in Brazil with no relocation support. Work worldwide.',
        ):
            with self.subTest(text=text):
                self.assertEqual(self.eligibility(text),'excluded')

    def test_decimal_experience_is_not_its_fractional_digit(self):
        result=self.fit('Required: Python. 2.5 years of experience.')
        self.assertEqual(result['experience_requirement_years'],2.5)
        self.assertEqual(result['decision'],'recommended')

    def test_experience_does_not_require_the_literal_word_experience(self):
        self.assertEqual(self.fit('Required: Python. At least 20 years in backend development.')['decision'],'excluded')

    def test_duration_variants_keep_thresholds_and_preference_context(self):
        for clause,years,decision in (
            ('At least 3 years in backend development.',3,'recommended'),
            ('3.5+ years of professional experience.',3.5,'stretch'),
            ('2.5–4 years of experience.',2.5,'recommended'),
            ('At least 20 years building APIs.',20,'excluded'),
            ('Nice to have:\nAt least 20 years in backend development.',None,'recommended'),
        ):
            with self.subTest(clause=clause):
                result=self.fit('Required: Python.\n'+clause)
                self.assertEqual(result['experience_requirement_years'],years)
                self.assertEqual(result['decision'],decision)

    def test_preferred_clause_does_not_erase_required_clause(self):
        result=self.fit('Python is required; Go is preferred.')
        self.assertIn('Python',result['required_skills'])
        self.assertEqual(result['decision'],'recommended')

    def test_later_alternative_does_not_erase_earlier_requirement(self):
        go_facts={'tech':[['Languages','Go']],'experience':[],'projects':[],'never_add':[],'years_experience':3}
        result=self.fit('Required: Python.\nExperience with Python or Go.',go_facts)
        self.assertNotEqual(result['decision'],'recommended')
        self.assertIn('Python',result['required_skills'])

    def test_mixed_clauses_preserve_each_requirement(self):
        for text in (
            'Python is required; Go is preferred.',
            'Go is preferred; Python is required.',
            'Python is required and Go is preferred.',
            'Go is preferred but Python is required.',
        ):
            with self.subTest(text=text):
                result=self.fit(text)
                self.assertIn('Python',result['required_skills'])
                self.assertIn('Go',result['preferred_skills'])
                self.assertNotIn('Go',result['required_skills'])
                self.assertEqual(result['decision'],'recommended')

    def test_denied_expertise_is_not_confirmed_expertise(self):
        facts=copy.deepcopy(FACTS)
        facts['experience'][0]['bullets'].append('No experience with Linux.')
        self.assertNotEqual(self.fit('Required: Python.\nExperience with Linux.',facts)['decision'],'recommended')

    def test_expertise_requires_positive_claims_and_respects_never_add(self):
        for claim,forbidden,expected in (
            ('I have not used Linux.',[],'excluded'),
            ('No experience with Linux or networking.',[],'excluded'),
            ('No networking experience, but maintained Linux servers.',[],'recommended'),
            ('Not only Linux administration but also REST APIs.',[],'recommended'),
            ('Maintained Linux servers.',['Linux'],'excluded'),
        ):
            with self.subTest(claim=claim):
                facts=copy.deepcopy(FACTS)
                facts['experience'][0]['bullets'].append(claim)
                facts['never_add']+=forbidden
                result=self.fit('Required: Python.\nExperience with Linux.',facts)
                self.assertEqual(result['decision'],expected)

    def test_denied_technology_cannot_establish_skill_overlap(self):
        facts={'tech':[],'experience':[{'bullets':['No experience with Python.']}],'projects':[],'never_add':[]}
        result=self.fit('Required: Python.',facts)
        self.assertEqual(result['matched_skills'],[])
        self.assertEqual(result['decision'],'excluded')

    def test_country_exception_stops_pipeline_before_renderer(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); data=root/'data'; data.mkdir()
            (data/'cv_facts.json').write_text(json.dumps(FACTS),encoding='utf-8')
            (data/'preferences.json').write_text(json.dumps(PREFS),encoding='utf-8')
            confirm(root,FACTS['name'])
            report={'scout':'worldwide','count':1,'sources':[{'platform':'ashby','company':'fictional','status':'healthy','jobs':1}],
                    'errors':[],'candidates':[{'company':'fictional','title':'Backend Engineer','location':'Remote, Global',
                    'url':'https://example.com/job','description':'Required: Python. Work from anywhere except Tunisia.'}]}
            with redirect_stdout(io.StringIO()),patch('morning.render_files') as renderer:
                result=run_workflow(root,[report],render=True,read_mail=False)
            self.assertEqual(renderer.call_count,0,'Excluded country reached the application-resume renderer')


if __name__=='__main__':
    unittest.main(verbosity=2)
