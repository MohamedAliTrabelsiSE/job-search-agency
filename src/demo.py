"""Run a fictional search in a separate private folder; no network, mail or submissions."""
import argparse
import shutil
from pathlib import Path
from morning import ROOT, run_workflow
from profile import confirm
from load_config import load_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT/'tmp/demo')
    p.add_argument('--no-render', action='store_true')
    args = p.parse_args()
    if args.root.resolve() == ROOT.resolve():
        p.error('Demo must use a separate root; it cannot replace the real profile.')
    data = args.root/'data'
    data.mkdir(parents=True, exist_ok=True)
    for source, dest in [('cv_facts.example.json','cv_facts.json'),('preferences.example.json','preferences.json')]:
        target = data/dest
        if target.exists() and load_json(target) != load_json(ROOT/'config'/source):
            p.error('Demo root contains another profile. Select a new empty --root.')
        shutil.copyfile(ROOT/'config'/source, target)
    confirm(args.root, 'Ada Okonkwo')
    result = run_workflow(args.root, load_json(ROOT/'tests/fixtures/scout-reports.json')['reports'],
                          render=not args.no_render, read_mail=False)
    return int(result['status'] == 'failed' or bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
