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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from load_config import load_json, load_simple_yaml
from check_ready import ensure_ready
from screen import (
    classify_sponsorship,
    classify_worldwide,
    location_ok,
    parse_date,
    plain,
    seniority_blocked,
    title_ok,
    within_cutoff,
)

ROOT = Path(__file__).resolve().parents[1]
UA = "job-search-agency/0.1 (public posting reader; does not apply)"


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def board_jobs(platform, slug):
    if platform == "ashby":
        data = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
        jobs = []
        for job in data.get("jobs") or []:
            if job.get("isListed") is False:
                continue
            loc = job.get("location") or ""
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
            })
        return jobs
    if platform == "lever":
        data = fetch(f"https://api.lever.co/v0/postings/{slug}?mode=json")
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
                "description": job.get("descriptionPlain") or job.get("description") or "",
            })
        return jobs
    if platform == "greenhouse":
        data = fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
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
    if not title_ok(job["title"], rules):
        return False
    if seniority_blocked(job["title"], rules):
        return False
    if not location_ok(job["location"], rules):
        return False
    if not within_cutoff(job["published"], rules, today=today):
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Read public job boards into candidates.json")
    parser.add_argument("--sources", default=str(ROOT / "config" / "sources.example.yaml"))
    parser.add_argument("--rules", default=str(ROOT / "config" / "rules.example.yaml"))
    parser.add_argument("--skip", default=str(ROOT / "data" / "roles.json"), help="Applied and rejected companies")
    parser.add_argument("--out", default=str(ROOT / "data" / "candidates.json"))
    parser.add_argument("--content-cap", type=int, default=20, help="Max Greenhouse description fetches")
    args = parser.parse_args()

    ensure_ready(ROOT)
    sources = load_simple_yaml(args.sources)
    rules = load_simple_yaml(args.rules)
    skip = skipped_companies(args.skip)

    errors = []
    found = []
    tasks = []
    for platform in ("ashby", "lever", "greenhouse"):
        for slug in sources.get(platform) or []:
            tasks.append((platform, slug))

    def run(task):
        platform, slug = task
        try:
            return platform, slug, board_jobs(platform, slug), None
        except Exception as exc:
            return platform, slug, [], str(exc)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, tasks))

    pending_content = []
    for platform, slug, jobs, error in results:
        if error:
            errors.append({"platform": platform, "company": slug, "error": error})
            continue
        if slug.lower() in skip:
            continue
        for job in jobs:
            if keep(job, rules):
                if platform == "greenhouse" and not job["description"]:
                    pending_content.append(job)
                else:
                    found.append(job)

    capped = pending_content[: args.content_cap]
    left_out = len(pending_content) - len(capped)

    def fill(job):
        try:
            return hydrate_greenhouse(job["company"], job), None
        except Exception as exc:
            return job, str(exc)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for job, error in pool.map(fill, capped):
            if error:
                errors.append({"platform": "greenhouse", "company": job["company"], "error": error, "url": job.get("url")})
            found.append(job)

    candidates = []
    seen = set()
    for job in found:
        url = job.get("url") or ""
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        if rules.get("mode") == "worldwide":
            evidence = classify_worldwide(job.get("location") or "", job.get("description") or "", rules)
        else:
            evidence = classify_sponsorship(job.get("description") or "", rules)
        text = plain(job.get("description") or "")
        candidates.append({
            "platform": job["platform"],
            "company": job["company"],
            "title": job["title"],
            "location": job["location"],
            "url": url,
            "published": job.get("published") or "",
            "sponsorship": evidence["status"],
            "offer_phrases": evidence["offers"],
            "block_phrases": evidence["blocks"],
            "excerpt": text[:900],
        })

    rank = {"offered": 0, "conflict": 1, "unknown": 2, "blocked": 3}
    candidates.sort(key=lambda c: c.get("published") or "", reverse=True)
    candidates.sort(key=lambda c: rank.get(c["sponsorship"], 9))

    payload = {
        "source": "public posting APIs only; nothing was submitted",
        "count": len(candidates),
        "greenhouse_descriptions_skipped": left_out,
        "errors": errors,
        "candidates": candidates,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    by_status = {}
    for c in candidates:
        by_status[c["sponsorship"]] = by_status.get(c["sponsorship"], 0) + 1
    print(f"boards {len(tasks)}  errors {len(errors)}  candidates {len(candidates)}  {by_status}")
    print(f"wrote {out}")
    for c in candidates:
        if c["sponsorship"] == "offered":
            print(f"  offered  {c['published']}  {c['company']}  {c['title'][:48]}  {c['location'][:24]}")


if __name__ == "__main__":
    main()
