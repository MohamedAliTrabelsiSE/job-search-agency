"""Transparent technical matching. A score is evidence overlap, not a probability."""
import json
import re
from requirements import extract, expertise_in

SKILLS = {
    'TypeScript': ['typescript'], 'JavaScript': ['javascript'],
    'Node.js': ['node.js', 'nodejs', 'node js'], 'NestJS': ['nestjs', 'nest.js'],
    'React': ['react', 'react.js', 'reactjs'], 'Next.js': ['next.js', 'nextjs'],
    'React Native': ['react native'], 'Python': ['python'], 'Java': ['java'],
    'Go': ['go', 'golang'], 'Rust': ['rust'], 'Ruby': ['ruby'],
    'PostgreSQL': ['postgresql', 'postgres'], 'MongoDB': ['mongodb'],
    'REST APIs': ['rest', 'rest api', 'rest apis'], 'Docker': ['docker'],
    'Kubernetes': ['kubernetes', 'k8s'], 'AWS': ['aws', 'amazon web services'],
    'Azure': ['azure'], 'Git': ['git'], 'CI/CD': ['ci/cd', 'continuous integration'],
    'RabbitMQ': ['rabbitmq'], 'Kafka': ['kafka'], 'Jest': ['jest'],
    'Playwright': ['playwright'], 'Spring Boot': ['spring boot'],
    'WebSocket': ['websocket', 'websockets'], 'Supabase': ['supabase'],
    'LLM integration': ['llm', 'large language models', 'openai'],
    'Angular': ['angular'], 'Swift': ['swift'], 'SQL': ['sql'],
}


def skills_in(text):
    original = text
    text = text.lower()
    found = {name for name, aliases in SKILLS.items() if name != 'Go'
             and any(re.search(r'(?<![\w])' + re.escape(alias) + r'(?![\w])', text) for alias in aliases)}
    if re.search(r'\b(?:Go|[Gg]olang)\b', original):
        found.add('Go')
    return found


def compare(card, facts):
    text = card.get('description') or card.get('excerpt') or ''
    target = skills_in(card.get('title', '') + '\n' + text)
    known = skills_in(json.dumps({k: facts.get(k) for k in ('tech','experience','projects')}, ensure_ascii=False))
    known -= skills_in(' '.join(facts.get('never_add') or []))
    requirements=extract(card,skills_in)
    required=requirements['required']
    candidate_text=json.dumps({k:facts.get(k) for k in ('tech','experience','projects')})
    expertise=expertise_in(candidate_text,candidate=True)
    missing_expertise=sorted((requirements['essential_expertise']-expertise) | (requirements['essential_skills']-known))
    alternative_results=[dict(group,satisfied=bool(set(group['options']) & (known|expertise))) for group in requirements['alternatives']]
    missing_alternatives=[group for group in alternative_results if not group['satisfied']]
    shared = sorted(target & known)
    gaps = sorted(required - known)
    years_match = re.search(r'(\d+)\s*\+?\s*years?\s+(?:of\s+)?(?:relevant\s+|professional\s+|industry\s+)?experience', requirements['required_text'], re.I)
    years_required = int(years_match.group(1)) if years_match else None
    candidate_years = facts.get('years_experience')
    if candidate_years is None:
        summary = facts.get('summary') or ''
        match = re.search(r'\b(\d+|one|two|three|four|five)\s+years?\s+(?:of experience|in industry)', summary, re.I)
        if match:
            raw = match.group(1).lower()
            candidate_years = int(raw) if raw.isdigit() else {'one':1,'two':2,'three':3,'four':4,'five':5}[raw]
    eligibility = card.get('eligibility') or {}
    status = eligibility.get('status', 'eligible')
    reasons=[]
    decision = 'excluded' if status == 'excluded' or not shared or missing_expertise else 'needs_verification' if status == 'needs_verification' or requirements['unresolved'] else 'stretch' if gaps or missing_alternatives else 'recommended'
    if missing_expertise:
        reasons.append('Missing essential expertise: '+', '.join(missing_expertise))
    if requirements['unresolved']:
        reasons.append('Mandatory expertise requires interpretation and evidence review.')
    if decision != 'excluded' and years_required is not None:
        if candidate_years is None:
            decision = 'needs_verification'
        elif candidate_years < years_required and decision != 'needs_verification':
            decision = 'stretch'
    # Exact technical overlap outranks arbitrary prose. Missing requirements
    # lower fit without pretending a skill gap makes an application illegal.
    score = max(0, len(shared) * 3 + len(required & known) * 2 - len(gaps) * 2)
    return {'score':score, 'why':', '.join(shared) if shared else 'no technical overlap with your resume',
            'matched_skills':shared, 'required_skills':sorted(required),
            'missing_required_skills':gaps, 'decision':decision,
            'preferred_skills':sorted(requirements['preferred']), 'one_of_requirements':alternative_results,
            'missing_essential_expertise':missing_expertise,'unresolved_requirements':requirements['unresolved'],
            'requirement_evidence':requirements['evidence'],'decision_reasons':reasons,
            'experience_requirement_years':years_required, 'confirmed_experience_years':candidate_years,
            'assessment_method':'deterministic skill aliases and requirement-line heuristics'}
