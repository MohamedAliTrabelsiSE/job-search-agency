"""Fetch public Ashby, Lever, and Greenhouse postings and write candidates.json.

This script reads job ads. It does not log in, open an application form,
or contact an employer. Boards that fail are recorded and skipped.

Usage (from the repo root):
    py -3 src/discover.py
    py -3 src/discover.py --sources config/sources.example.yaml --rules config/rules.example.yaml
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from load_config import load_json, load_simple_yaml
from check_ready import ensure_ready
from network import fetch
from eligibility import assess
from state import write_json
from ad_text import structured_text
from screen import (
    classify_sponsorship,
    classify_worldwide,
    location_ok,
    parse_date,
    plain,
    seniority_blocked,
    title_ok,
    within_cutoff,
    freshness,
)

ROOT = Path(__file__).resolve().parents[1]
UA = "job-search-agency/0.1 (public posting reader; does not apply)"


def board_jobs(platform, slug):
    if platform == "ashby":
        data = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
            raise ValueError('Malformed Ashby board response: expected jobs list')
        jobs = []
        for job in data.get("jobs") or []:
            if job.get("isListed") is False:
                continue
            loc = job.get("location") or ""
            if job.get('isRemote') and 'remote' not in loc.lower():
                loc = 'Remote, ' + loc
            extra = [s.get("location") for s in (job.get("secondaryLocations") or []) if s.get("location")]
            if extra:
                loc = f"{loc} {extra}"
            jobs.append({
                "platform": "ashby",
                "company": slug,
                "title": job.get("title") or "",
                "location": loc,
                "url": job.get("jobUrl") or job.get("applyUrl") or "",
                "published": (job.get("publishedAt") or "")[:10],
                "description": job.get("descriptionPlain") or "",
                "is_remote": job.get('isRemote'),
                "workplace_type": job.get('workplaceType') or '',
                "structured_locations": [job.get('location')]+extra,
            })
        return jobs
    if platform == "lever":
        data = fetch(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        if not isinstance(data, list):
            raise ValueError('Malformed Lever board response: expected posting list')
        jobs = []
        for job in data:
            published = parse_date(job.get("createdAt"))
            jobs.append({
                "platform": "lever",
                "company": slug,
                "title": job.get("text") or "",
                "location": (job.get("categories") or {}).get("location") or "",
                "url": job.get("hostedUrl") or "",
                "published": published.isoformat() if published else "",
                "is_remote": job.get('workplaceType') == 'remote',
                "workplace_type": job.get('workplaceType') or '',
                "description": (job.get("descriptionPlain") or job.get("description") or "") + '\n' + '\n'.join(
                    str(section.get('text') or '') + '\n' + str(section.get('content') or '')
                    for section in job.get('lists') or []) + '\n' + (job.get('additionalPlain') or job.get('additional') or ''),
            })
        return jobs
    if platform == "greenhouse":
        data = fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
            raise ValueError('Malformed Greenhouse board response: expected jobs list')
        jobs = []
        for job in data.get("jobs") or []:
            published = parse_date(job.get("updated_at"))
            jobs.append({
                "platform": "greenhouse",
                "company": slug,
                "id": job.get("id"),
                "title": job.get("title") or "",
                "location": (job.get("location") or {}).get("name") or "",
                "url": job.get("absolute_url") or "",
                "published": published.isoformat() if published else "",
                "description": "",
            })
        return jobs
    raise ValueError(f"Unknown platform {platform}")


def hydrate_greenhouse(slug, job):
    if not job.get("id"):
        return job
    data = fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job['id']}")
    job["description"] = data.get("content") or ""
    return job


def skipped_companies(path):
    """Companies already applied to or rejected. Missing file means nothing is skipped."""
    file = Path(path)
    if not file.exists():
        return set()
    data = load_json(file)
    names = []
    for key in ("applied", "rejected", "skipped"):
        names.extend(data.get(key) or [])
    return {n.lower() for n in names}


def keep(job, rules, today=None):
    if not title_ok(job["title"], rules, job.get('description') or ''):
        return False
    if seniority_blocked(job["title"], rules):
        return False
    if job.get('is_listed') is False:
        return False
    if rules.get('freshness_mode','prefer')=='recent_only' and freshness(job.get('published'),rules,today)['status']=='older':
        return False
    return True


def discover(sources, rules, preferences, skip=(), content_cap=None, board_reader=None):
    """Return candidates plus source health. Network failures stay distinct from no matches."""
    from source_health import coverage
    reader = board_reader or board_jobs
    tasks = [(platform, slug) for platform in ('ashby','lever','greenhouse') for slug in sources.get(platform) or []]
    def run(task):
        platform, slug = task
        try:
            jobs = reader(platform, slug)
            return jobs, {'platform':platform,'company':slug,'status':'healthy','jobs':len(jobs)}
        except Exception as exc:
            return [], {'platform':platform,'company':slug,'status':'failed','error':str(exc)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        reports = list(pool.map(run, tasks))
    health = [report for _, report in reports]
    errors = [report for report in health if report['status'] == 'failed']
    found, pending = [], []
    for jobs, report in reports:
        if report['company'].lower() in skip:
            continue
        for job in jobs:
            if keep(job, rules):
                if job['platform'] == 'greenhouse' and not job.get('description'):
                    pending.append(job)
                else:
                    found.append(job)
    capped = pending if content_cap is None else pending[:content_cap]
    def hydrate(job):
        try:
            return hydrate_greenhouse(job['company'], job), None
        except Exception as exc:
            return job, {'platform':'greenhouse','company':job['company'],'url':job.get('url'),'error':str(exc)}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for job, error in pool.map(hydrate, capped):
            if error:
                errors.append(error)
            found.append(job)
    candidates, seen = [], set()
    for job in found:
        key = job.get('url') or (job['company'],job['title'],job['location'])
        if key in seen:
            continue
        seen.add(key)
        raw = job.get('description') or ''
        text = structured_text(raw)
        path = 'worldwide' if rules.get('mode') == 'worldwide' else 'relocation'
        card = dict(job, description_raw=raw, description=text, excerpt=plain(text)[:900], path=path,
                    retrieved_at=datetime.now(timezone.utc).isoformat())
        card['freshness']=freshness(job.get('published'),rules)
        card['availability']={'status':'observed_listed','observed_at':card['retrieved_at']}
        card['eligibility'] = assess(card, preferences, path)
        card['sponsorship'] = {'eligible':'offered','excluded':'blocked'}.get(card['eligibility']['status'],'unknown')
        candidates.append(card)
    summary = coverage(health)
    left_out = len(pending)-len(capped)
    summary['limited'] |= bool(left_out or len(errors) > summary['failed'])
    return {'source':'configured public posting APIs only; nothing submitted', 'count':len(candidates),
            'coverage':summary, 'sources':health, 'errors':errors,
            'greenhouse_descriptions_skipped':left_out, 'candidates':candidates}


def main():
    parser = argparse.ArgumentParser(description="Read public job boards into candidates.json")
    parser.add_argument("--sources", default=str(ROOT / "config" / "sources.example.yaml"))
    parser.add_argument("--rules", default=str(ROOT / "config" / "rules.example.yaml"))
    parser.add_argument("--skip", default=str(ROOT / "data" / "roles.json"), help="Applied and rejected companies")
    parser.add_argument("--out", default=str(ROOT / "data" / "candidates.json"))
    parser.add_argument("--content-cap", type=int, default=None, help="Optional description limit; omitted means fetch every matching ad")
    parser.add_argument("--speaker", default="", help="Who is searching, printed on each line")
    args = parser.parse_args()

    ensure_ready(ROOT)
    sources = load_simple_yaml(args.sources)
    rules = load_simple_yaml(args.rules)
    skip = skipped_companies(args.skip)

    payload = discover(sources, rules, load_json(ROOT/'data/preferences.json'), skip, args.content_cap)
    write_json(args.out, payload)
    print(f"{args.speaker} coverage {payload['coverage']} candidates {payload['count']}")
    return 0 if payload['coverage']['healthy'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
