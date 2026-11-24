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
    'brazil':['brazil','brasil'], 'mexico':['mexico'], 'argentina':['argentina'],
    'chile':['chile'], 'colombia':['colombia'], 'peru':['peru'],
    'australia':['australia'], 'new zealand':['new zealand'], 'india':['india'],
    'japan':['japan'], 'singapore':['singapore'], 'china':['china'],
    'south africa':['south africa'], 'nigeria':['nigeria'], 'kenya':['kenya'],
}
EUROPE = {'germany','austria','netherlands','belgium','ireland','sweden','denmark','finland',
          'norway','france','poland','spain','portugal','italy','united kingdom'}
EMEA = EUROPE | {'tunisia','egypt','south africa','nigeria','kenya'}
REGIONS = {
    'north america':({'united states','canada','mexico'},['north america','north american']),
    'latam':({'mexico','brazil','argentina','chile','colombia','peru'},['latam','latin america']),
    'south america':({'brazil','argentina','chile','colombia','peru'},['south america']),
    'apac':({'australia','new zealand','india','japan','singapore','china'},['apac','asia pacific']),
    'emea':(EMEA,['emea']), 'europe':(EUROPE,['europe','european']),
    'eu':(EUROPE-{'united kingdom','norway'},['eu','european union']),
}
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
    workplace = (job.get('workplace_type') or '').lower()
    attendance=re.search(r'hybrid (?:work|role|position)|office attendance required|\d+ days? (?:per week|a week|/week).{0,30}(?:office|on.?site)|in[- ]person (?:role|work|position)|(?:role|position|work) (?:is |requires? )?(?:on[- ]site|in[- ]person)|on[- ]site in', description, re.I)
    if workplace in {'onsite','on-site','hybrid'} or attendance:
        result['status'] = 'excluded'
        result['reasons'].append('The role requires hybrid or office attendance, not fully remote work.')
        result['evidence'].append({'field':'work_arrangement','quote':attendance.group(0) if attendance else workplace,'meaning':'office_required'})
        return result
    restrictions=[]
    unknown=[]
    def add_scope(scope, is_location=False):
        members=countries(scope)
        regions=[(name,group) for name,(group,aliases) in REGIONS.items() if any(contains(scope,a) for a in aliases)]
        if members:
            restrictions.append(members)
        elif regions:
            # EU is narrower than Europe; select the narrowest named region.
            restrictions.append(min((group for _,group in regions),key=len))
        elif is_location:
            remainder=re.sub(r'\b(?:remote|home based|home-based|global|worldwide|anywhere|distributed)\b','',scope,flags=re.I)
            if re.search(r'[a-z]',remainder,re.I):
                unknown.append(scope)
        else:
            unknown.append(scope)
        if members or regions or scope in unknown:
            result['evidence'].append({'field':'remote_countries','quote':scope.strip(),'meaning':'restriction' if members or regions else 'unrecognized_restriction'})
    add_scope(location,True)
    for sentence in re.split(r'(?<=[.!?])\s+|\n+',description):
        if re.search(r'must be based|residen|(?:candidates?|applicants?) .{0,25}(?:based|located)|hiring (?:only |in |from )|remote (?:from|in)|(?:europe|eu|america|apac|latam)[- ]only|only .{0,20}(?:europe|america|apac|latam)|based in|located in|(?:eligible|authorized|right) to work in|must (?:live|reside)|(?:role|position|hiring).{0,35}\bonly\b',sentence,re.I):
            add_scope(sentence)
    # A supported restriction can exclude; unknown geography cannot establish
    # eligibility even when a company description says "worldwide".
    if current in COUNTRIES and any(current not in group for group in restrictions):
        result['status'] = 'excluded'
        result['reasons'].append('Remote hiring is restricted to other countries.')
    elif unknown or (restrictions and current not in COUNTRIES):
        result['reasons'].append('Verify unrecognized hiring geography before applying.')
    elif restrictions and current and ('remote' in text.lower() or job.get('is_remote')):
        result['status'] = 'eligible'
    elif re.search(r'work from anywhere|anywhere in the world|worldwide|remote[, -]+global', text, re.I):
        result['status'] = 'eligible'
        result['evidence'].append({'field':'remote_countries','quote':location or description, 'meaning':'worldwide'})
    else:
        result['reasons'].append('Remote does not establish permission to work from the current country.')
    if result['status'] != 'excluded' and not (re.search(r'remote|anywhere|worldwide', text, re.I) or job.get('is_remote')):
        result['status'] = 'needs_verification'
        result['reasons'].append('Fully remote work is not explicit.')
    return result
