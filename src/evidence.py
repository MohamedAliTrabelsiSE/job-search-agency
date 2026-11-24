"""Conservative clause boundaries for positive evidence, not keyword presence."""
import re


def independent_clauses(text):
    # Commas and "and" split only before a new subject, not in lists such as
    # "no experience with Linux and networking".
    subject=r'(?:this|it|we|you|the (?:role|position|company)|our (?:team|company)|office attendance|candidates?|applicants?)\b'
    return re.split(r'[;\n]+|(?<=[.!?])\s+|\b(?:but|however|yet|while)\b|(?:,\s*|\band\s+)(?='+subject+r')',text,flags=re.I)


def positive_clauses(text):
    """Keep affirmative clauses; a denied claim cannot establish a capability.

    Separate independent contrast clauses so a denial does not erase later
    positive evidence. Ambiguous negative clauses are deliberately not evidence.
    """
    for clause in independent_clauses(text):
        if not re.search(r"\b(?:no|nor|never|without|lack(?:s|ing)?|not(?!\s+only\b))\b|n['’]t\b", clause, re.I):
            yield clause


def positive_claim_text(value):
    """Read individual profile values so negation cannot cross JSON fields."""
    if isinstance(value, str):
        return '\n'.join(positive_clauses(value))
    if isinstance(value, dict):
        return '\n'.join(positive_claim_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return '\n'.join(positive_claim_text(item) for item in value)
    return ''
