"""Check public boards and record source health without implying global coverage."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from discover import board_jobs
from load_config import load_simple_yaml
from state import Store, now, write_json

ROOT = Path(__file__).resolve().parents[1]


def check_sources(paths):
    tasks = sorted({(platform, company) for path in paths
                    for platform, companies in load_simple_yaml(path).items()
                    for company in companies})
    def check(task):
        platform, company = task
        try:
            jobs = board_jobs(platform, company)
            return {'platform':platform, 'company':company, 'status':'healthy', 'jobs':len(jobs), 'checked_at':now()}
        except Exception as exc:
            return {'platform':platform, 'company':company, 'status':'failed', 'error':str(exc), 'checked_at':now()}
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(check, tasks))


def coverage(reports):
    unique = {(r['platform'],r['company']):r for r in reports}
    healthy = sum(r['status'] == 'healthy' for r in unique.values())
    return {'attempted':len(unique), 'healthy':healthy, 'failed':len(unique)-healthy,
            'board_checks':len(reports), 'limited':healthy < len(unique),
            'scope':'configured company boards only; not the entire job market'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', nargs='+', type=Path)
    p.add_argument('--out', type=Path, default=ROOT/'data/source-health.json')
    args = p.parse_args()
    reports = check_sources(args.sources or sorted((ROOT/'config/sources').glob('*.yaml')))
    result = {'checked_at':now(), 'coverage':coverage(reports), 'sources':reports}
    write_json(args.out, result)
    Store(args.out.parent).record_sources(reports)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['coverage']['healthy'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
