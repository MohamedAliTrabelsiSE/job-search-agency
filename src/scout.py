"""Run the scouts that match data/preferences.json.

Each scout is one call of discover.py with that region's boards and rules.
They do not see each other's results. The merger does.
"""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_ready import ensure_ready
from load_config import load_json
from places import scouts_for

ROOT = Path(__file__).resolve().parents[1]

RULES = {
    "worldwide": ROOT / "config" / "rules.worldwide.yaml",
    "dach": ROOT / "config" / "rules.relocation.yaml",
    "benelux-ie": ROOT / "config" / "rules.relocation.yaml",
    "nordics": ROOT / "config" / "rules.relocation.yaml",
}


def scout_plan(preferences):
    plan = []
    for name in scouts_for(preferences):
        sources = ROOT / "config" / "sources" / f"{name}.yaml"
        rules = RULES.get(name)
        if sources.exists() and rules is not None:
            plan.append((name, sources, rules))
    return plan


def main():
    ensure_ready(ROOT)
    preferences = load_json(ROOT / "data" / "preferences.json")
    plan = scout_plan(preferences)
    if not plan:
        sys.stderr.write("No scout matches this interest. Add a place the source list covers, or choose remote.\n")
        return 2
    skip = ROOT / "data" / "roles.json"
    out_dir = ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    def run_one(item):
        name, sources, rules = item
        out = out_dir / f"scout-{name}.json"
        cmd = [
            sys.executable,
            str(ROOT / "src" / "discover.py"),
            "--sources", str(sources),
            "--rules", str(rules),
            "--out", str(out),
        ]
        if skip.exists():
            cmd.extend(["--skip", str(skip)])
        print(f"scout {name}", flush=True)
        return subprocess.run(cmd).returncode

    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = list(pool.map(run_one, plan))
    return 1 if any(codes) else 0


if __name__ == "__main__":
    sys.exit(main())
