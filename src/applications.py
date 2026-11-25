"""Prepare and record applications locally. This module never submits or sends."""
import argparse
import json
from pathlib import Path
from state import Store, write_json

ROOT = Path(__file__).resolve().parents[1]


def preflight(card, answers, store):
    missing = [key for key in ('gross_annual_salary','currency','availability','education_category','visa_sponsorship_required')
               if answers.get(key) is None or answers.get(key) == '']
    previous = store.application(card)
    invalid = []
    salary = answers.get('gross_annual_salary')
    if salary is not None and (isinstance(salary, bool) or not isinstance(salary, (int,float)) or salary <= 0):
        invalid.append('gross_annual_salary must be a positive number')
    currency = answers.get('currency')
    if currency is not None and (not isinstance(currency,str) or len(currency) != 3 or not currency.isalpha() or not currency.isupper()):
        invalid.append('currency must be a three-letter uppercase code')
    if answers.get('visa_sponsorship_required') is not None and not isinstance(answers['visa_sponsorship_required'],bool):
        invalid.append('visa_sponsorship_required must be true or false')
    blocked = bool(previous and previous['status'] in ('submitted','duplicate_blocked'))
    if not card.get('url'):
        missing.append('job_url')
    return {'ready':not missing and not invalid and not blocked, 'missing':missing, 'invalid':invalid, 'previous':previous,
            'submission_approval_required':True, 'note':'Ready means answers are present, not permission or confirmed eligibility.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--card', type=Path, required=True)
    sub = p.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare'); prep.add_argument('--answers', type=Path, required=True)
    rec = sub.add_parser('record')
    rec.add_argument('--status', choices=['approved','submitted','duplicate_blocked','failed'], required=True)
    rec.add_argument('--evidence', required=True)
    rec.add_argument('--user-approved', action='store_true', help='Operator attests explicit approval of this specific job')
    args = p.parse_args()
    card = json.loads(args.card.read_text(encoding='utf-8'))
    store = Store(args.root/'data')
    if args.command == 'prepare':
        answers = json.loads(args.answers.read_text(encoding='utf-8'))
        result = preflight(card, answers, store)
        write_json(args.card.parent/'preflight.json', result)
        if result['ready']:
            store.record_application(card, 'prepared', {'answers':answers})
        print(json.dumps(result, indent=2))
        return 0 if result['ready'] else 2
    if args.status == 'approved' and not args.user_approved:
        p.error('Record explicit user approval using --user-approved for this card.')
    if args.status == 'submitted':
        previous = store.application(card)
        if not previous or previous['status'] != 'approved':
            p.error('Record specific user approval before recording submission.')
    store.record_application(card, args.status, {'evidence':args.evidence})
    print('Recorded observed outcome; no application was sent by this command.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
