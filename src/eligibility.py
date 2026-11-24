"""Conservative eligibility with separate sponsorship and relocation evidence."""
import re
from screen import plain

COUNTRIES = {
    'germany': ['germany', 'berlin', 'hamburg', 'munich'],
    'austria': ['austria', 'vienna'],
    'netherlands': ['netherlands', 'amsterdam', 'rotterdam'],
    'belgium': ['belgium', 'brussels'], 'ireland': ['ireland', 'dublin'],
    'sweden': ['sweden', 'stockholm'], 'denmark': ['denmark', 'copenhagen'],
    'finland': ['finland', 'helsinki'], 'norway': ['norway', 'oslo'],
    'france': ['france', 'paris'], 'poland': ['poland', 'warsaw'],
    'spain': ['spain', 'madrid', 'barcelona'], 'portugal': ['portugal', 'lisbon'],
    'italy': ['italy', 'milan', 'rome'], 'united kingdom': ['united kingdom', 'uk', 'london'],
    'united states': ['united states', 'usa', 'us'], 'canada': ['canada', 'toronto'],
    'tunisia': ['tunisia', 'tunis'], 'egypt': ['egypt', 'cairo'],
}
EMEA = set(COUNTRIES) - {'united states', 'canada'}
EUROPE = EMEA - {'tunisia', 'egypt'}
VISA_YES = ['visa sponsorship', 'visa support', 'we sponsor work visas', 'we sponsor visas']
VISA_NO = ['no visa sponsorship', 'no visa support', 'unable to offer visa sponsorship',
           'not able to offer visa sponsorship', 'cannot sponsor', 'do not sponsor',
           "don't sponsor", 'unable to sponsor', 'existing right to work',
           'must already have the right to work', 'visa sponsorship is not available',
           'visa sponsorship is unavailable', 'visa sponsorship is not offered',
           'visa support is not available', 'without visa sponsorship']
MOVE_YES = ['relocation support', 'relocation package', 'relocation assistance']
MOVE_NO = ['no relocation support', 'no relocation assistance', 'no relocation']


def contains(text, term):
    return bool(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I))


def countries(text):
    return {country for country, aliases in COUNTRIES.items() if any(contains(text, a) for a in aliases)}


def _signals(text, yes, no, field):
    masked = text.lower()
    evidence = []
    negatives = [p for p in no if contains(masked, p)]
    for phrase in negatives:
        evidence.append({'field': field, 'quote': phrase, 'meaning': 'not_offered'})
        masked = masked.replace(phrase, ' ')
    positives = [p for p in yes if contains(masked, p)]
    evidence += [{'field': field, 'quote': p, 'meaning': 'offered'} for p in positives]
    status = 'conflicting' if positives and negatives else 'not_offered' if negatives else 'offered' if positives else 'unknown'
    return status, evidence


def assess(job, preferences, path):
    location = plain(job.get('location') or '')
    description = plain(job.get('description') or job.get('excerpt') or '')
    text = location + '\n' + description
    visa, evidence = _signals(description, VISA_YES, VISA_NO, 'visa_sponsorship')
    move, move_evidence = _signals(description, MOVE_YES, MOVE_NO, 'relocation_assistance')
    result = {'status': 'needs_verification', 'visa_sponsorship': visa,
              'relocation_assistance': move, 'work_locations': sorted(countries(location)),
              'evidence': evidence + move_evidence, 'reasons': []}
    if path != 'worldwide':
        wanted = {p.lower() for p in preferences.get('places', [])}
        locations = countries(location)
        if locations and not locations & wanted:
            result['status'] = 'excluded'
            result['reasons'].append('Location is outside the selected relocation countries.')
        elif visa == 'not_offered' and preferences.get('needs_visa_sponsorship', True):
            result['status'] = 'excluded'
            result['reasons'].append('Ad refuses sponsorship or requires existing work rights.')
        elif (visa == 'offered' or preferences.get('needs_visa_sponsorship') is False) and locations & wanted:
            result['status'] = 'eligible'
        else:
            result['reasons'].append('Confirm work-visa sponsorship and the hiring location with the employer.')
        return result

    current = (preferences.get('current_country') or '').lower()
    if re.search(r'hybrid (?:work|role|position)|office attendance required|\d+ days? (?:per week|a week|/week).{0,30}(?:office|on.?site)', description, re.I):
        result['status'] = 'excluded'
        result['reasons'].append('The role requires hybrid or office attendance, not fully remote work.')
        return result
    # Country restrictions in the ad take precedence over a bare "Remote" label.
    restrictions = []
    for sentence in re.split(r'[\n.!?]', description):
        if re.search(r'only|must be based|residen|based in|located in|hiring in|remote (?:from|in)', sentence, re.I):
            found = countries(sentence)
            if found:
                restrictions.append(found)
                result['evidence'].append({'field':'remote_countries','quote':sentence.strip(), 'meaning':'restriction'})
    loc_countries = countries(location)
    if loc_countries:
        restrictions.append(loc_countries)
        result['evidence'].append({'field':'remote_countries','quote':location,'meaning':'restriction'})
    if any(current not in group for group in restrictions):
        result['status'] = 'excluded'
        result['reasons'].append('Remote hiring is restricted to other countries.')
    elif restrictions and current and 'remote' in text.lower():
        result['status'] = 'eligible'
    elif re.search(r'(?:europe|eu)\s*(?:only|[- ]based)|only.{0,20}(?:europe|eu)\b', text, re.I) and current not in EUROPE:
        result['status'] = 'excluded'
        result['reasons'].append('Explicit Europe-only remote restriction excludes the current country.')
    elif re.search(r'work from anywhere|anywhere in the world|worldwide|remote[, -]+global', text, re.I):
        result['status'] = 'eligible'
        result['evidence'].append({'field':'remote_countries','quote':location or description, 'meaning':'worldwide'})
    elif contains(text, 'EMEA') and current in EMEA:
        result['status'] = 'eligible'
        result['evidence'].append({'field':'remote_countries','quote':location, 'meaning':'EMEA'})
    elif contains(text, 'Europe') and current not in EUROPE:
        result['status'] = 'excluded'
        result['reasons'].append('Europe-only remote work does not include the current country.')
    else:
        result['reasons'].append('Remote does not establish permission to work from the current country.')
    if not re.search(r'remote|anywhere|worldwide', text, re.I):
        result['status'] = 'needs_verification'
        result['reasons'].append('Fully remote work is not explicit.')
    return result
