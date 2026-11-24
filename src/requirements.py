"""Requirement sections, alternatives and explicit essential expertise evidence."""
import re
from ad_text import structured_text

PREFERRED=r'nice[- ]to[- ]have|preferred(?: qualifications| skills)?|bonus(?: points)?|desirable|optional'
REQUIRED=r'requirements|required(?: qualifications| skills)?|qualifications|must[- ]haves?|what (?:you bring|we(?: are|\x27re) looking for)'
OTHER=r'responsibilities|what you(?: will|\x27ll) do|about (?:us|the company|the role)|benefits|what we offer'
EXPERTISE={
    'Linux administration':(r'\blinux(?: administration| systems?| engineering)?\b',r'linux (?:administration|systems?|engineering)|administered linux|maintained linux'),
    'Networking':(r'\bnetworking\b|network (?:protocols|engineering|administration)|tcp/ip',r'networking|network (?:protocols|engineering|administration)|tcp/ip'),
    'Cloud infrastructure':(r'cloud (?:infrastructure|engineering|operations|architecture)',r'cloud (?:infrastructure|engineering|operations|architecture)'),
    'Distributed systems':(r'distributed systems',r'distributed systems'),
    'Compiler engineering':(r'compiler (?:engineering|development|design)',r'compiler (?:engineering|development|design)'),
}


def expertise_in(text,candidate=False):
    return {name for name,patterns in EXPERTISE.items() if re.search(patterns[int(candidate)],text,re.I)}


def extract(card,skills_in):
    text=structured_text(card.get('description') or card.get('excerpt') or '')
    # Recover explicit headings even in legacy flattened ad snapshots.
    text=re.sub(r'(?i)\b('+PREFERRED+'|'+REQUIRED+r')\s*:',r'\n\1:\n',text)
    context=None
    required=set(card.get('required_skills') or []) | skills_in(card.get('title') or '')
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
        if re.search(PREFERRED,line,re.I):
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
        grouped=set()
        for clause in re.split(r'[,;]|\band\b(?!/or)',line,flags=re.I):
            choices=skills_in(clause) | expertise_in(clause)
            if len(choices)>1 and re.search(r'\bor\b|/',clause,re.I):
                alternatives.append({'options':sorted(choices),'quote':clause.strip()})
                grouped |= choices
        required -= grouped
        required |= skills-grouped
        essentials |= domains-grouped
        if re.search(r'\b(?:expert|advanced|deep knowledge)\b',line,re.I):
            essential_skills |= skills-grouped
        for phrase in re.findall(r'(?:expertise in|expert in|advanced knowledge of|deep knowledge of)\s+([^.;]+)',line,re.I):
            if not skills_in(phrase) and not expertise_in(phrase):
                unresolved.append(phrase.strip())
        if re.search(r'\b(?:expert|expertise|essential|advanced|deep knowledge)\b',line,re.I) and not skills and not domains:
            unresolved.append(line)
    return {'required':required,'preferred':preferred,'alternatives':alternatives,
            'essential_expertise':essentials,'essential_skills':essential_skills,'unresolved':unresolved,'evidence':evidence,
            'required_text':'\n'.join(required_lines)}
