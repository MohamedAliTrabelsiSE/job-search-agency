"""Employer discovery consumes public search evidence, not a fixed token list."""
import sys
import unittest
import json
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from employers import discover_employers, merge_sources,load_discovery


class EmployerTest(unittest.TestCase):
    def test_missing_invalid_and_expired_evidence_are_explicitly_seed_only(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'discovery.json'
            self.assertEqual(load_discovery(p)['market_discovery']['mode'],'seed_only')
            p.write_text('not json')
            self.assertEqual(load_discovery(p)['market_discovery']['mode'],'seed_only')
            p.write_text(json.dumps({'verified_at':'2020-01-01T00:00:00+00:00','boards':[], 'market_discovery':{'mode':'expanded'}}))
            self.assertEqual(load_discovery(p)['market_discovery']['mode'],'seed_only')
    def test_outside_employer_is_verified_and_duplicates_collapse(self):
        data={'queries':['fictional search'], 'results':[
            {'url':'https://jobs.ashbyhq.com/new-employer/job-one','query':'fictional search'},
            {'url':'https://jobs.ashbyhq.com/new-employer/job-two','query':'fictional search'},
            {'url':'https://jobs.ashbyhq.com.evil.example/fake/job'},
        ]}
        calls=[]
        def reader(platform,company):
            calls.append((platform,company)); return [{'title':'Backend Engineer'}]
        result=discover_employers(data,reader)
        self.assertEqual(calls,[('ashby','new-employer')])
        self.assertEqual(len(result['boards']),1)
        self.assertTrue(result['rejected'])
        sources=merge_sources({'ashby':['seed']},result['boards'],'worldwide')
        self.assertEqual(sources['ashby'],['new-employer','seed'])
        self.assertFalse(result['market_discovery']['exhaustive'])

    def test_failed_board_is_not_admitted(self):
        def fail(*args): raise OSError('fixture unavailable')
        result=discover_employers({'results':[{'url':'https://jobs.lever.co/new-company/1'}]},fail)
        self.assertEqual(result['boards'],[])
        self.assertTrue(result['rejected'])


if __name__=='__main__': unittest.main()
