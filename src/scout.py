"""Scout threads share the process-wide request budget and write isolated reports."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from check_ready import ensure_ready
from discover import discover, skipped_companies
from load_config import load_json, load_simple_yaml
from names import SCOUTS
from places import scouts_for
from state import write_json

ROOT = Path(__file__).resolve().parents[1]
RULES = {name: ROOT/'config'/('rules.worldwide.yaml' if name == 'worldwide' else 'rules.relocation.yaml')
         for name in SCOUTS}


def scout_plan(preferences):
    return [(name, ROOT/'config/sources'/f'{name}.yaml', RULES[name])
            for name in scouts_for(preferences) if (ROOT/'config/sources'/f'{name}.yaml').exists()]


def run_scouts(preferences, out_dir, roles_path=None):
    plan = scout_plan(preferences)
    if not plan:
        raise ValueError('No scout covers these preferences. Add supported sources before searching.')
    skip = skipped_companies(roles_path) if roles_path else set()
    def run_one(item):
        name, sources, rules = item
        print(f'{SCOUTS[name]} searching {name}', flush=True)
        payload = discover(load_simple_yaml(sources), load_simple_yaml(rules), preferences, skip)
        payload['scout'] = name
        write_json(Path(out_dir)/f'scout-{name}.json', payload)
        print(f"{SCOUTS[name]} coverage {payload['coverage']} candidates {payload['count']}", flush=True)
        return payload
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(run_one, plan))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT/'data')
    args = parser.parse_args()
    ensure_ready(ROOT)
    reports = run_scouts(load_json(ROOT/'data/preferences.json'), args.out_dir, ROOT/'data/roles.json')
    return 0 if any(r['coverage']['healthy'] for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
