"""Explicit onboarding confirmation, bound to the contents reviewed by the person."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from state import write_json

ROOT = Path(__file__).resolve().parents[1]


def digest(facts, preferences):
    return hashlib.sha256(json.dumps([facts, preferences], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate(facts, preferences):
    errors = []
    if not isinstance(facts, dict) or not isinstance(preferences, dict):
        return ['Facts and preferences must be JSON objects.']
    for key in ('name','email','headline_default','location','languages'):
        if not isinstance(facts.get(key), str) or not facts[key].strip():
            errors.append('Missing resume field: ' + key)
    for key in ('experience','projects','education','tech','never_add'):
        if not isinstance(facts.get(key), list):
            errors.append('Resume field must be a list: ' + key)
    for section, keys in [('experience',('title','company','dates','bullets')), ('projects',('name','bullets')), ('education',('degree','school','dates'))]:
        for item in facts.get(section, []) if isinstance(facts.get(section), list) else []:
            if not isinstance(item, dict) or any(k not in item for k in keys):
                errors.append('Incomplete entry in ' + section)
            elif 'bullets' in keys and (not isinstance(item['bullets'], list) or not all(isinstance(b,str) for b in item['bullets'])):
                errors.append('Invalid bullets in ' + section)
    interest = preferences.get('interest')
    if 'years_experience' in facts and (isinstance(facts['years_experience'],bool) or not isinstance(facts['years_experience'],(int,float)) or facts['years_experience']<0):
        errors.append('years_experience must be a confirmed nonnegative number.')
    policy=preferences.get('matching_policy',{})
    if not isinstance(policy,dict):
        errors.append('matching_policy must be an object.')
    else:
        for key,low,high in [('max_experience_gap',0,50),('min_experience_ratio',0,1)]:
            if key in policy and (isinstance(policy[key],bool) or not isinstance(policy[key],(int,float)) or not low<=policy[key]<=high):
                errors.append('Invalid matching policy: '+key)
    if interest not in ('remote','relocate','both'):
        errors.append('Interest must be remote, relocate or both.')
    if not preferences.get('current_country'):
        errors.append('Current country is required.')
    if 'needs_visa_sponsorship' in preferences and not isinstance(preferences['needs_visa_sponsorship'], bool):
        errors.append('needs_visa_sponsorship must be true or false when supplied.')
    work = preferences.get('work_right')
    if not isinstance(work, dict):
        errors.append('Work-right statements are required.')
        work = {}
    if interest in ('remote','both') and not work.get('remote'):
        errors.append('Confirm remote work from the current country.')
    if interest in ('relocate','both'):
        if not isinstance(preferences.get('places'), list) or not preferences['places']:
            errors.append('Select relocation countries.')
        if not work.get('relocation'):
            errors.append('Confirm relocation work-right requirements.')
    return errors


def read_profile(root):
    data = Path(root) / 'data'
    return tuple(json.loads((data / name).read_text(encoding='utf-8')) for name in ('cv_facts.json','preferences.json'))


def confirm(root, name):
    facts, preferences = read_profile(root)
    errors = validate(facts, preferences)
    if errors:
        raise ValueError('\n'.join(errors))
    if name.strip().casefold() != facts['name'].strip().casefold():
        raise ValueError('Confirmation name does not match the resume.')
    write_json(Path(root) / 'data/profile-confirmation.json',
               {'name':facts['name'], 'digest':digest(facts, preferences), 'confirmed_at':datetime.now(timezone.utc).isoformat()})


def ready_errors(root):
    try:
        facts, preferences = read_profile(root)
        errors = validate(facts, preferences)
        p = Path(root) / 'data/profile-confirmation.json'
        confirmation = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        if confirmation.get('digest') != digest(facts, preferences):
            errors.append('Profile is unconfirmed or changed. Review facts/preferences, then confirm this revision.')
        return errors
    except (OSError, ValueError, TypeError) as exc:
        return ['Cannot read profile: ' + str(exc)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('show')
    c = sub.add_parser('confirm'); c.add_argument('--name', required=True)
    sub.add_parser('fresh-start', help='Archive private profile and history; never delete the previous profile')
    args = parser.parse_args()
    if args.command == 'show':
        facts, preferences = read_profile(args.root)
        print(json.dumps({'facts':facts,'preferences':preferences}, ensure_ascii=False, indent=2))
    elif args.command == 'confirm':
        confirm(args.root, args.name)
        print('Profile revision confirmed.')
    else:
        data = args.root / 'data'
        archive = data / 'archives' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        archive.mkdir(parents=True)
        # Move only explicitly owned private state; no recursive deletion.
        for name in ('cv_facts.json','preferences.json','profile-confirmation.json','roles.json','agency.sqlite3','latest-run.json','inbox.json'):
            p = data / name
            if p.exists():
                p.rename(archive / name)
        print('Archived private setup to ' + str(archive) + '. Complete onboarding before searching.')


if __name__ == '__main__':
    main()
