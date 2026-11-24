"""Requirement sections, alternatives and explicit essential expertise evidence."""
import re
from ad_text import structured_text

PREFERRED=r'nice[- ]to[- ]have(?: skills)?|(?:preferred|desired)(?: qualifications| skills(?: and experience)?)?|bonus(?: points)?|desirable|optional'
REQUIRED=r'skills, requirements and qualifications|requirements|required(?: qualifications| skills(?: and experience)?)?|qualifications|must[- ]haves?|who you are|what (?:you bring|we(?: are|[\x27’]re) looking for(?: in you)?)'
OTHER=r'responsibilities|what you(?: will|[\x27’]ll) do|about (?:us|the company|the role|canonical)|benefits|what we offer(?: colleagues)?|what is canonical\??'
EXPERTISE={
    'Linux':(r'\b(?:linux|ubuntu|debian)\b',r'\b(?:linux|ubuntu|debian)\b'),
    'Linux administration':(r'linux (?:administration|systems? administration|engineering)',r'linux (?:administration|systems? administration|engineering)|administered linux|maintained linux'),
    'Networking':(r'\bnetworking\b|network (?:protocols|engineering|administration)|tcp/ip',r'networking|network (?:protocols|engineering|administration)|tcp/ip'),
    'Cloud infrastructure':(r'cloud (?:infrastructure|engineering|operations|architecture)',r'cloud (?:infrastructure|engineering|operations|architecture)'),
    'Distributed systems':(r'distributed systems',r'distributed systems'),
    'Compiler engineering':(r'compiler (?:engineering|development|design)',r'compiler (?:engineering|development|design)'),
    'Blockchain':(r'blockchain (?:industry|engineering|development)|multichain|onchain',r'blockchain|multichain|onchain'),
    'Kernel engineering':(r'kernel (?:engineering|development)|kernel internals',r'kernel (?:engineering|development)|kernel internals'),
}


def expertise_in(text,candidate=False):
    return {name for name,patterns in EXPERTISE.items() if re.search(patterns[int(candidate)],text,re.I)}


def extract(card,skills_in):
    text=structured_text(card.get('description') or card.get('excerpt') or '')
    # Recover explicit headings even in legacy flattened ad snapshots.
    text=re.sub(r'(?i)\b('+PREFERRED+'|'+REQUIRED+r')\s*:',r'\n\1:\n',text)
    text=re.sub(r'(?i)\b(nice[- ]to[- ]have(?: skills)?|what we are looking for(?: in you)?|skills, requirements and qualifications|what we offer(?: colleagues)?)\b',r'\n\1\n',text)
    context=None
    required=set(card.get('required_skills') or [])
    inferred=skills_in(card.get('title') or '')
    preferred=set()
    essentials=set()
    essential_skills=set()
    alternatives=[]
    evidence=[]
    unresolved=[]
    required_lines=[]
    for line in re.split(r'\n+|(?<=[.!?])\s+',text):
        line=line.strip(' \t-•:')
        if not line:
            continue
        if re.fullmatch(PREFERRED,line,re.I):
            context='preferred'; continue
        if re.fullmatch(REQUIRED,line,re.I):
            context='required'; continue
        if re.fullmatch(OTHER,line,re.I):
            context=None; continue
        mode=context
        outer=re.sub(r'\([^)]*\)','',line)
        if re.search(r'^(?:'+PREFERRED+r')\b|\b(?:preferred|optional)\b|\bnot (?:strictly )?required\b',outer,re.I):
            mode='preferred'
        elif re.search(r'\brequired\b|must[- ]have|hands[- ]on|proficien|experience (?:with|in)|strong .*knowledge|\bessential\b',line,re.I):
            mode=mode or 'required'
        if mode not in ('required','preferred'):
            continue
        skills=skills_in(line)
        domains=expertise_in(line)
        evidence.append({'kind':mode,'quote':line,'skills':sorted(skills),'expertise':sorted(domains)})
        if mode=='preferred':
            preferred |= skills
            continue
        required_lines.append(line)
        if re.search(r'\b(?:two|three|[2-9]) (?:or more )?of\b|\bat least (?:two|three|[2-9])\b',line,re.I):
            unresolved.append(line)
            continue  # Cardinality is not an ordinary one-of alternative.
        if re.search(r'academic (?:track record|performance)|ability to travel|security clearance',line,re.I):
            unresolved.append(line)
        grouped=set()
        def parenthesized(match):
            choices=skills_in(match.group(1)) | expertise_in(match.group(1))
            if len(choices)>1:
                alternatives.append({'options':sorted(choices),'quote':match.group(0)})
                grouped.update(choices)
                return ''
            return match.group(0)
        parse_line=re.sub(r'\(([^()]*(?:\bor\b|one of|any of)[^()]*)\)',parenthesized,line,flags=re.I)
        clauses=re.split(r'\band\b(?!/or)|;',parse_line,flags=re.I)
        choice_marker=r'\bor\b|\b(?:one|any) of\b|\beither\b'
        clauses=[part for clause in clauses for part in ([clause] if re.search(choice_marker,clause,re.I) else clause.split(','))]
        for clause in clauses:
            choices=skills_in(clause) | expertise_in(clause)
            if len(choices)>1 and re.search(choice_marker+r'|/',clause,re.I):
                alternatives.append({'options':sorted(choices),'quote':clause.strip()})
                grouped |= choices
        required -= grouped
        required |= skills-grouped
        essentials |= domains-grouped
        if re.search(r'\b(?:expert|advanced|deep knowledge|deeply familiar)\b',line,re.I):
            essential_skills |= skills-grouped
        for phrase in re.findall(r'(?:expertise in|expert in|advanced knowledge of|deep knowledge of)\s+([^.;]+)',line,re.I):
            if not skills_in(phrase) and not expertise_in(phrase):
                unresolved.append(phrase.strip())
        if re.search(r'\b(?:expert|expertise|essential|advanced|deep knowledge)\b',line,re.I) and not skills and not domains:
            unresolved.append(line)
        if not skills and not domains and re.search(r'\b(?:experience|knowledge|familiarity|understanding|proficiency)\b',line,re.I) and not re.search(r'years?|English|communication|agile|software development',line,re.I):
            unresolved.append(line)
        # Unknown named technologies are uncertainty, not silently satisfied
        # requirements merely because another technology on the line overlaps.
        generic={'API','APIs','SDK','SDKs','AI','UI','UX','STEM','CS','CI','CD','HTTP','REST','SQL','E2E'}
        named=re.findall(r'\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b|\b[A-Z]{2,}\b',line)
        if any(word not in generic and not skills_in(word) and not expertise_in(word) for word in named):
            unresolved.append(line)
    grouped_all={option for group in alternatives for option in group['options']}
    required |= inferred-preferred-grouped_all
    return {'required':required,'preferred':preferred,'alternatives':alternatives,
            'essential_expertise':essentials,'essential_skills':essential_skills,'unresolved':list(dict.fromkeys(unresolved)),'evidence':evidence,
            'required_text':'\n'.join(required_lines)}
