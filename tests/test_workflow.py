"""Behavioral regressions, using fictional candidate and employer data only."""
import copy
import json
import sys
import tempfile
import unittest
import io
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from eligibility import assess
from load_config import load_json
from rank import rank_cards
from merge import merge_cards
from ats_check import findings
from draft_cv import draft
from profile import confirm, ready_errors
from state import Store
from morning import run_workflow
from unittest.mock import patch
from render_cv import render_files, build, normalize
from discover import discover
from applications import preflight
from state import job_key
from state import write_json
from concurrent.futures import ThreadPoolExecutor
import threading
import time

FACTS = load_json(ROOT / 'config/cv_facts.example.json')
PREFS = load_json(ROOT / 'config/preferences.example.json')


class EligibilityTest(unittest.TestCase):
    def test_hybrid_attendance_overrides_global_remote_marketing(self):
        result = assess({'location':'Remote, Global','description':'This hybrid role requires 3 days per week in the office.'}, PREFS, 'worldwide')
        self.assertEqual(result['status'], 'excluded')

    def test_negative_sponsorship_word_order_is_respected(self):
        result = assess({'location':'Berlin','description':'Visa sponsorship is not available.'}, PREFS, 'relocation')
        self.assertEqual(result['visa_sponsorship'], 'not_offered')

    def test_existing_work_rights_do_not_require_a_sponsorship_offer(self):
        prefs = dict(PREFS, needs_visa_sponsorship=False)
        result = assess({'location':'Berlin','description':'We cannot sponsor.'}, prefs, 'relocation')
        self.assertEqual(result['status'], 'eligible')
    def test_relocation_help_does_not_confirm_a_visa(self):
        result = assess({'location':'Berlin, Germany', 'description':'We offer relocation support.'}, PREFS, 'relocation')
        self.assertEqual(result['visa_sponsorship'], 'unknown')
        self.assertEqual(result['relocation_assistance'], 'offered')
        self.assertEqual(result['status'], 'needs_verification')
        self.assertIn('relocation support', result['evidence'][0]['quote'].lower())

    def test_remote_emea_can_include_egypt(self):
        result = assess({'location':'Remote, EMEA', 'description':'Work remotely from EMEA.'}, PREFS, 'worldwide')
        self.assertEqual(result['status'], 'eligible')

    def test_bare_remote_does_not_override_country_restrictions(self):
        result = assess({'location':'Remote', 'description':'Only residents of Canada may apply.'}, PREFS, 'worldwide')
        self.assertEqual(result['status'], 'excluded')


class MatchingTest(unittest.TestCase):
    def test_common_words_are_not_a_match(self):
        kept, skipped = rank_cards([{'company':'demo','title':'Other','excerpt':'the and for'}], FACTS)
        self.assertEqual(kept, [])
        self.assertEqual(len(skipped), 1)

    def test_go_as_an_ordinary_verb_is_not_a_technical_requirement(self):
        kept, _ = rank_cards([{'title':'Backend Engineer','description':'TypeScript. We go further together.'}], FACTS)
        self.assertNotIn('Go', kept[0]['missing_required_skills'])

    def test_unknown_experience_requirement_needs_verification(self):
        kept, _ = rank_cards([{'title':'Backend Engineer','description':'TypeScript. Required: 5 years of experience.'}], FACTS)
        self.assertEqual(kept[0]['decision'], 'needs_verification')

    def test_full_description_and_required_gap_control_the_decision(self):
        cards = [
            {'company':'goco','title':'Go Backend Developer','description':'Required: hands-on Go experience. REST APIs.'},
            {'company':'tsco','title':'Backend Engineer','excerpt':'Our company builds products.',
             'description':'Required: TypeScript, NodeJS, REST APIs.'},
        ]
        kept, _ = rank_cards(cards, FACTS)
        self.assertEqual(kept[0]['company'], 'tsco')
        self.assertEqual(kept[1]['decision'], 'stretch')
        self.assertIn('Go', kept[1]['missing_required_skills'])

    def test_different_jobs_at_one_company_are_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'scout-worldwide.json'
            p.write_text(json.dumps({'candidates':[
                {'company':'demo','title':'Backend','url':'https://example.com/1','sponsorship':'offered'},
                {'company':'demo','title':'Fullstack','url':'https://example.com/2','sponsorship':'offered'},
            ]}), encoding='utf-8')
            self.assertEqual(len(merge_cards([p], {})), 2)

    def test_verified_remote_route_beats_uncertain_relocation_for_the_same_job(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for region,status in [('dach','needs_verification'),('worldwide','eligible')]:
                p = Path(folder)/f'scout-{region}.json'
                p.write_text(json.dumps({'candidates':[{'company':'demo','title':'Backend',
                    'url':'https://example.com/1','eligibility':{'status':status}}]}), encoding='utf-8')
                paths.append(p)
            cards = merge_cards(paths,{})
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]['path'], 'worldwide')

    def test_bare_remote_is_unconfirmed(self):
        self.assertEqual(assess({'location':'Remote','description':'Build APIs.'}, PREFS, 'worldwide')['status'], 'needs_verification')

    def test_country_outside_preferences_is_excluded(self):
        result = assess({'location':'Oslo, Norway','description':'We offer visa sponsorship.'}, PREFS, 'relocation')
        self.assertEqual(result['status'], 'excluded')

    def test_negated_sponsorship_is_not_an_offer(self):
        result = assess({'location':'Berlin','description':'No visa sponsorship. Relocation assistance is available.'}, PREFS, 'relocation')
        self.assertEqual(result['visa_sponsorship'], 'not_offered')
        self.assertEqual(result['status'], 'excluded')


class FactsTest(unittest.TestCase):
    def test_two_roles_at_the_same_employer_remain_distinct(self):
        facts = copy.deepcopy(FACTS)
        other = copy.deepcopy(facts['experience'][0]); other['title'] = 'Software Developer'; other['dates'] = '2023 - 2024'
        facts['experience'].append(other)
        card = {'path':'worldwide'}
        self.assertEqual(findings(draft(facts, PREFS, card), facts, card, PREFS), [])
    def test_invented_metric_is_blocked(self):
        card = {'path':'worldwide','title':'Engineer','description':'TypeScript'}
        cv = draft(FACTS, PREFS, card)
        cv['experience'][0]['bullets'].append('Improved performance by 999%.')
        self.assertTrue(any(x['severity'] == 'factual' for x in findings(cv, FACTS, card)))

    def test_dropped_roles_projects_and_languages_are_blocked(self):
        card = {'path':'worldwide'}
        cv = draft(FACTS, PREFS, card)
        cv['experience'] = []; cv['projects'] = []; cv['languages'] = ''
        issues = findings(cv, FACTS, card)
        self.assertGreaterEqual(len(issues), 3)

    def test_modified_date_and_unclaimed_skill_are_blocked(self):
        card = {'path':'worldwide'}
        cv = draft(FACTS, PREFS, card)
        cv['experience'][0]['dates'] = '1999 - present'
        cv['tech'][0][1] += ', Rust'
        self.assertGreaterEqual(len(findings(cv, FACTS, card)), 2)

    def test_freeform_claim_and_altered_contact_do_not_pass(self):
        card = {'path':'worldwide'}
        cv = draft(FACTS, PREFS, card)
        cv['summary'] += ' Managed an international engineering department.'
        cv['contact'][0][0] = '+00 123456789'
        quotes = [issue['quote'] for issue in findings(cv, FACTS, card)]
        self.assertIn('overview provenance', quotes)
        self.assertIn('contact', quotes)


class StateTest(unittest.TestCase):
    def test_atomic_json_supports_a_long_windows_workspace(self):
        (ROOT/'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            base = Path(folder)
            # Include the destination filename but leave room for a short sibling.
            leaf = base/('x' * max(5, 218-len(str(base))))
            path = leaf/'card.json'
            write_json(path, {'company':'fictional'})
            self.assertEqual(load_json(path), {'company':'fictional'})
    def test_confirmation_is_invalidated_by_changed_preferences(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)/'data'; data.mkdir()
            (data/'cv_facts.json').write_text(json.dumps(FACTS), encoding='utf-8')
            (data/'preferences.json').write_text(json.dumps(PREFS), encoding='utf-8')
            self.assertTrue(ready_errors(folder))
            confirm(folder, FACTS['name'])
            self.assertEqual(ready_errors(folder), [])
            prefs = copy.deepcopy(PREFS); prefs['current_country'] = 'Tunisia'
            (data/'preferences.json').write_text(json.dumps(prefs), encoding='utf-8')
            self.assertTrue(ready_errors(folder))

    def test_duplicate_blocks_only_the_same_job_and_needs_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            card = {'company':'demo','url':'https://example.com/jobs/1'}
            with self.assertRaises(ValueError):
                store.record_application(card, 'submitted', {})
            store.record_application(card, 'duplicate_blocked', {'evidence':'Employer duplicate notice'})
            self.assertEqual(store.application(dict(card, url=card['url']+'/application'))['status'], 'duplicate_blocked')
            self.assertIsNone(store.application(dict(card, url='https://example.com/jobs/2')))
            self.assertEqual(store.application_history(card)[0]['status'], 'duplicate_blocked')
            with self.assertRaises(ValueError):
                store.record_application(card, 'prepared', {})
            self.assertFalse(preflight(card, {}, store)['ready'])

    def test_tracking_parameters_do_not_hide_job_identity(self):
        self.assertNotEqual(job_key({'url':'https://example.com/careers?gh_jid=1'}), job_key({'url':'https://example.com/careers?gh_jid=2'}))
        self.assertEqual(job_key({'url':'https://example.com/jobs/1?utm_source=test'}), job_key({'url':'https://example.com/jobs/1'}))


class DiscoveryTest(unittest.TestCase):
    def test_full_ad_and_board_failure_are_preserved(self):
        import datetime
        from load_config import load_simple_yaml
        rules = load_simple_yaml(ROOT/'config/rules.worldwide.yaml')
        description = ('Company introduction. ' * 100) + 'Required: TypeScript. Work from anywhere in the world.'
        def reader(platform, company):
            if company == 'offline':
                raise OSError('fixture board failure')
            return [{'platform':'ashby','company':company,'title':'Backend Engineer','location':'Remote, Global',
                     'url':'https://example.com/1','published':datetime.date.today().isoformat(),'description':description}]
        report = discover({'ashby':['healthy','offline']}, rules, PREFS, board_reader=reader)
        self.assertEqual(report['coverage']['healthy'], 1)
        self.assertTrue(report['coverage']['limited'])
        self.assertEqual(report['candidates'][0]['description'], description)
        self.assertEqual(report['candidates'][0]['eligibility']['status'], 'eligible')

    def test_malformed_board_is_a_failure_instead_of_an_empty_success(self):
        from discover import board_jobs
        with patch('discover.fetch', return_value={'error':'board unavailable'}):
            with self.assertRaisesRegex(ValueError, 'Malformed'):
                board_jobs('ashby','fictional')

    def test_shared_budget_bounds_concurrent_network_requests(self):
        from network import fetch
        lock = threading.Lock()
        counts = {'active':0,'peak':0}
        class Response:
            def __enter__(self):
                with lock:
                    counts['active'] += 1
                    counts['peak'] = max(counts['peak'],counts['active'])
                return self
            def read(self):
                time.sleep(0.01)
                return b'{"jobs":[]}'
            def __exit__(self, *args):
                with lock:
                    counts['active'] -= 1
        with patch('urllib.request.urlopen', side_effect=lambda *a, **k: Response()):
            with ThreadPoolExecutor(max_workers=24) as pool:
                results = list(pool.map(lambda i: fetch('https://example.com/'+str(i)), range(24)))
        self.assertEqual(len(results), 24)
        self.assertGreater(counts['peak'], 1)
        self.assertLessEqual(counts['peak'], 8)


class PipelineTest(unittest.TestCase):
    def test_document_keeps_clickable_contact_and_project_links(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'resume.docx'
            build(normalize(draft(FACTS, PREFS, {'path':'worldwide'})), path)
            targets = {r.target_ref for r in Document(path).part.rels.values() if r.is_external}
            self.assertIn('mailto:ada.okonkwo@example.com', targets)
            self.assertIn('https://github.com/example', targets)
            self.assertIn('https://github.com/example/sample-api', targets)
    def setUp(self):
        output = patch('sys.stdout', new=io.StringIO())
        output.start()
        self.addCleanup(output.stop)
    def setup_profile(self, root):
        data = root/'data'; data.mkdir()
        (data/'cv_facts.json').write_text(json.dumps(FACTS), encoding='utf-8')
        (data/'preferences.json').write_text(json.dumps(PREFS), encoding='utf-8')
        confirm(root, FACTS['name'])

    def test_isolated_run_ranks_and_holds_without_reading_stale_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.setup_profile(root)
            (root/'data/scout-stale.json').write_text(json.dumps({'candidates':[{'company':'stale'}]}))
            reports = load_json(ROOT/'tests/fixtures/scout-reports.json')['reports']
            result = run_workflow(root, reports, render=False, read_mail=False)
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['coverage']['failed'], 1)
            self.assertEqual(len(result['folders']), 2)
            self.assertEqual(len(result['needs_verification']), 1)
            run = root/'data/runs'/result['run_id']
            shortlist = load_json(run/'shortlist.json')
            self.assertEqual([x['decision'] for x in shortlist['cards']], ['recommended','stretch','needs_verification'])
            self.assertNotIn('stale', json.dumps(shortlist))
            self.assertEqual(shortlist['skipped'][0]['company'], 'example-canada')
            for output in result['folders']:
                self.assertEqual(load_json(Path(output)/'ats.json')['verdict'], 'pass')
                self.assertFalse((Path(output)/'resume.pdf').exists())

    def test_all_failed_sources_do_not_replace_the_last_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.setup_profile(root)
            latest = root/'data/latest-run.json'; latest.write_text('{"run_id":"previous-success"}')
            report = {'scout':'worldwide','sources':[{'platform':'ashby','company':'offline','status':'failed'}], 'candidates':[]}
            result = run_workflow(root, [report], render=False, read_mail=False)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(load_json(latest)['run_id'], 'previous-success')

    def test_conversion_failure_preserves_previous_pdf_and_docx(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out/'resume.pdf').write_bytes(b'%PDF-old')
            (out/'resume.docx').write_bytes(b'old docx')
            cv = draft(FACTS, PREFS, {'path':'worldwide'})
            with patch('render_cv.to_pdf', side_effect=RuntimeError('fixture converter failure')):
                with self.assertRaisesRegex(RuntimeError, 'fixture converter failure'):
                    render_files(cv, out, PREFS)
            self.assertEqual((out/'resume.pdf').read_bytes(), b'%PDF-old')
            self.assertEqual((out/'resume.docx').read_bytes(), b'old docx')


if __name__ == '__main__':
    unittest.main()
