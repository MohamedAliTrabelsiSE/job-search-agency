"""Expand seeds from search-tool results and verify official public ATS boards.

The assistant performs web searches; this CLI never scrapes a search engine.
Without imported search evidence the run explicitly reports seed-only coverage.
"""
import argparse
import copy
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from discover import board_jobs
from state import now,write_json
from check_ready import ensure_ready
from profile import read_profile

ROOT=Path(__file__).resolve().parents[1]
HOSTS={'jobs.ashbyhq.com':'ashby','jobs.lever.co':'lever',
       'job-boards.greenhouse.io':'greenhouse','boards.greenhouse.io':'greenhouse'}


def queries(facts,prefs):
    from matching import skills_in
    known=skills_in(json.dumps(facts.get('tech') or []))-skills_in(' '.join(facts.get('never_add') or []))
    priority=['TypeScript','Node.js','NestJS','Python','JavaScript','Java','React']
    stack=[skill for skill in priority if skill in known]+sorted(known-set(priority))
    common=' '.join(stack[:5])+' software developer'
    scope='(site:jobs.ashbyhq.com OR site:jobs.lever.co OR site:job-boards.greenhouse.io)'
    searches=[]
    if prefs.get('interest') in ('remote','both'):
        searches.append(f'{common} remote worldwide {scope}')
        searches.append(f'{common} remote {prefs.get("current_country","")} EMEA {scope}')
    if prefs.get('interest') in ('relocate','both'):
        searches.append(f'{common} visa sponsorship relocation '+ ' OR '.join(prefs.get('places') or [])+' '+scope)
    return searches


def board_from_url(url):
    parts=urlsplit(url)
    if parts.scheme!='https' or parts.hostname not in HOSTS or parts.username or parts.port not in (None,443):
        raise ValueError('Search result is not a supported official ATS URL.')
    tokens=[p for p in parts.path.split('/') if p]
    if not tokens or not re.fullmatch(r'[A-Za-z0-9_-]+',tokens[0]):
        raise ValueError('No valid company board token in the result URL.')
    return HOSTS[parts.hostname],tokens[0]


def discover_employers(search_data,board_reader=None):
    reader=board_reader or board_jobs
    candidates={}; rejected=[]
    for result in search_data.get('results',[]):
        try:
            key=board_from_url(result.get('url',''))
            candidates.setdefault(key,[]).append(result)
        except (ValueError,TypeError) as exc:
            rejected.append({'url':result.get('url'),'error':str(exc)})
    def verify(item):
        (platform,company),evidence=item
        try:
            jobs=reader(platform,company)
            return {'platform':platform,'company':company,'verified_at':now(),
                    'job_count':len(jobs),'evidence':evidence,'scouts':sorted({s for e in evidence for s in e.get('scouts',['worldwide'])})},None
        except Exception as exc:
            return None,{'platform':platform,'company':company,'error':str(exc)}
    boards=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for board,error in pool.map(verify,candidates.items()):
            if error: rejected.append(error)
            else: boards.append(board)
    return {'verified_at':now(),'boards':boards,'rejected':rejected,
            'market_discovery':{'mode':'expanded' if boards else 'seed_only','queries':search_data.get('queries',[]),
             'results_reviewed':len(search_data.get('results',[])),'verified_boards':len(boards),
             'exhaustive':False,'scope':'Search-tool results plus configured seeds; not the entire job market.'}}


def merge_sources(seeds,boards,scout):
    merged=copy.deepcopy(seeds)
    for board in boards:
        if scout in board.get('scouts',['worldwide']):
            merged.setdefault(board['platform'],[]).append(board['company'])
    return {platform:sorted(set(tokens)) for platform,tokens in merged.items()}


def load_discovery(path):
    if not Path(path).exists():
        return {'boards':[],'market_discovery':{'mode':'seed_only','exhaustive':False,'reason':'No search-tool results imported. Run employer discovery before claiming broad coverage.'}}
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        verified=datetime.fromisoformat(data['verified_at'])
        if not isinstance(data['boards'],list) or not isinstance(data['market_discovery'],dict):
            raise ValueError('Invalid discovery schema')
        age=(datetime.now(timezone.utc)-verified).total_seconds()
    except (OSError,ValueError,KeyError,TypeError):
        return {'boards':[],'market_discovery':{'mode':'seed_only','exhaustive':False,'reason':'Invalid discovery evidence; rerun employer discovery.'}}
    if age<0 or age>7*86400:
        return {'boards':[],'market_discovery':{'mode':'seed_only','exhaustive':False,'reason':'Discovery evidence is older than seven days; refresh public searches.'}}
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('queries')
    importer=sub.add_parser('import'); importer.add_argument('--results',type=Path,required=True)
    args=p.parse_args()
    ensure_ready(args.root)
    if args.command=='queries':
        print(json.dumps({'queries':queries(*read_profile(args.root))},indent=2))
    else:
        result=discover_employers(json.loads(args.results.read_text(encoding='utf-8')))
        write_json(args.root/'data/employer-discovery.json',result)
        print(json.dumps(result['market_discovery'],indent=2))
        return 0 if result['boards'] else 1
    return 0


if __name__=='__main__': raise SystemExit(main())
