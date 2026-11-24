"""Run an evidence-based search; record results and stop before any submission."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from ats_check import findings, revise
from check_ready import ensure_ready
from draft_cv import draft
from load_config import load_json
from merge import merge_cards
from rank import rank_cards
from render_cv import render_files
from scout import run_scouts
from source_health import coverage
from state import Store, job_key, write_json
from eligibility import assess
from places import scouts_for

ROOT = Path(__file__).resolve().parents[1]


def slug(text):
    value = ''.join(c.lower() if c.isalnum() else '-' for c in text)
    return '-'.join(part for part in value.split('-') if part)[:48] or 'role'


def run_workflow(root=ROOT, reports=None, render=True, read_mail=True):
    root = Path(root).resolve()
    ensure_ready(root)
    facts = load_json(root/'data/cv_facts.json')
    prefs = load_json(root/'data/preferences.json')
    store = Store(root/'data')
    run_id, run_dir = store.start_run()
    summary = {'run_id':run_id, 'status':'running', 'folders':[], 'errors':[], 'nothing_submitted':True, 'rendering_requested':render}
    try:
        print('Ida reading the mail.' if read_mail else 'Ida skipped: isolated run; inbox not read.', flush=True)
        if read_mail:
            # Inbox has its own credential check. Isolated roots must not touch the real mailbox.
            if root.resolve() != ROOT.resolve():
                raise ValueError('Inbox access is available only for the repository root.')
            code = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'src/inbox.py'), '--out', str(run_dir/'inbox.json')]).returncode
            if code:
                raise RuntimeError('Inbox step failed.')
        else:
            write_json(run_dir/'inbox.json', {'skipped':'disabled for this run','messages':[]})
        if reports is None:
            reports = run_scouts(prefs, run_dir, root/'data/roles.json')
        reports = [report for report in reports if report.get('scout','worldwide') in scouts_for(prefs)]
        paths = []
        for report in reports:
            name = report.get('scout', 'worldwide')
            if name not in scouts_for(prefs):
                continue
            report = dict(report)
            kind = 'worldwide' if name == 'worldwide' else 'relocation'
            report['candidates'] = [dict(card, eligibility=assess(card, prefs, kind)) for card in report.get('candidates', [])]
            path = run_dir/f'scout-{name}.json'
            if path in paths:
                raise ValueError('Duplicate scout report: ' + name)
            write_json(path, dict(report, run_id=run_id))
            paths.append(path)
        health = [source for report in reports for source in report.get('sources', [])]
        store.record_sources(health)
        summary['coverage'] = coverage(health)
        summary['coverage']['limited'] |= any(report.get('errors') or report.get('greenhouse_descriptions_skipped') for report in reports)
        write_json(run_dir/'source-health.json', {'coverage':summary['coverage'],'sources':health})
        if not summary['coverage']['healthy']:
            raise RuntimeError('All configured sources failed; this is not a no-jobs result.')
        print('Sami pooling jobs from this run only.', flush=True)
        roles_path = root/'data/roles.json'
        roles = load_json(roles_path) if roles_path.exists() else {}
        cards = merge_cards(paths, roles)
        cards = [card for card in cards if not (store.application(card) or {}).get('status') in ('submitted','duplicate_blocked')]
        write_json(run_dir/'pool.json', {'cards':cards,'count':len(cards)})
        print('Theo ranking technical fit and reporting gaps.', flush=True)
        kept, skipped = rank_cards(cards, facts, prefs.get('matching_policy'))
        for path in paths:
            for excluded in load_json(path).get('candidates', []):
                if excluded.get('eligibility', {}).get('status') == 'excluded':
                    skipped.append(dict(excluded, decision='excluded', why='; '.join(excluded['eligibility']['reasons'])))
        write_json(run_dir/'shortlist.json', {'cards':kept,'skipped':skipped,'count':len(kept)})
        summary['shortlisted'] = len(kept)
        summary['needs_verification'] = [card for card in kept if card['decision'] == 'needs_verification']
        reviews = []
        for card in kept:
            if card['decision'] == 'needs_verification':
                continue
            import hashlib
            suffix = hashlib.sha256(job_key(card).encode()).hexdigest()[:8]
            base = root/'outbox'/run_id
            label = slug(card['company'])[:20]+'-'+slug(card['title'])[:24]
            budget = 220 - len(str(base)) - 1 - len(suffix) - 1
            if budget < 8:
                raise ValueError('Output root is too long for portable resume paths; select a shorter --root.')
            folder = base/(label[:budget]+'-'+suffix)
            folder.mkdir(parents=True, exist_ok=True)
            write_json(folder/'card.json', card)
            print(f"Maya drafting {card['company']} / {card['title']}. Marco checking confirmed facts.", flush=True)
            cv = draft(facts, prefs, card)
            first = findings(cv, facts, card, prefs)
            if first:
                cv = revise(cv, first, facts, prefs, card)
            remaining = findings(cv, facts, card, prefs)
            write_json(folder/'cv.json', cv)
            check = {'verdict':'block' if remaining else 'pass', 'findings':remaining,
                     'first_pass_findings':first, 'revision_count':int(bool(first)),
                     'checks':{'facts':'blocked' if remaining else 'checked', 'pdf':'not_checked'},
                     'job_fit_gaps':card['missing_required_skills'], 'eligibility':card.get('eligibility')}
            reviews.append({'card':card,'first':first,'remaining':remaining,'folder':str(folder)})
            if not remaining:
                try:
                    if render:
                        render_files(cv, folder, prefs)
                        check['checks']['pdf'] = 'rendered; visual review still required'
                    summary['folders'].append(str(folder))
                except Exception as exc:
                    check['checks']['pdf'] = 'failed'
                    summary['errors'].append({'job':job_key(card),'error':str(exc)})
            else:
                summary['errors'].append({'job':job_key(card),'error':'Resume blocked by factual findings.'})
            write_json(folder/'ats.json', check)
        summary['status'] = 'partial' if summary['errors'] or summary['coverage']['limited'] else 'complete'
        write_json(run_dir/'reviews.json', reviews)
        lines = ['# Search handoff', '', f"Run: {run_id}", f"Coverage: {summary['coverage']}",
                 f'Theo: {len(kept)} shortlisted, {len(skipped)} excluded.',
                 f"Needs eligibility verification (no resume): {len(summary['needs_verification'])}"]
        for report in reports:
            lines.append(f"{report.get('scout')}: {report.get('count',0)} candidates; {len(report.get('errors',[]))} errors.")
        for review in reviews:
            lines.append(f"Maya -> Marco: {review['card']['company']} / {review['card']['title']}")
            lines.append('Marco -> Maya: ' + ('blocked' if review['remaining'] else 'facts checked') +
                         (' after one revision.' if review['first'] else '; no revision.'))
            lines.extend(str(path) for path in sorted(Path(review['folder']).iterdir()) if path.is_file())
        lines += ['', 'Nothing submitted or sent. PDF rendering is separate from visual or ATS-parser validation.']
        (run_dir/'thread.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
        # Publish pointers only after processing; old successful runs remain intact.
        write_json(root/'data/latest-run.json', {'run_id':run_id,'folder':str(run_dir),'status':summary['status']})
    except Exception as exc:
        summary['status'] = 'failed'
        summary['errors'].append({'error':str(exc)})
    write_json(run_dir/'summary.json', summary)
    store.finish_run(run_id, summary['status'], summary)
    console = dict(summary, needs_verification=len(summary.get('needs_verification',[])), run_folder=str(run_dir))
    print(json.dumps(console, ensure_ascii=False, indent=2), flush=True)
    return summary


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--fixture', type=Path, help='Use fictional scout reports without network')
    p.add_argument('--no-render', action='store_true', help='Exercise decisions/facts without generating PDFs')
    p.add_argument('--skip-inbox', action='store_true')
    args = p.parse_args()
    reports = load_json(args.fixture)['reports'] if args.fixture else None
    result = run_workflow(args.root, reports, not args.no_render, not (args.skip_inbox or args.fixture))
    return 1 if result['status'] == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
