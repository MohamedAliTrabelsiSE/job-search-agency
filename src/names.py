"""The cast. The job title stays the source of truth. The name is how the morning speaks."""

LEAD = "Sami"
INBOX = "Ida"
RANKER = "Theo"
WRITER = "Maya"
ATS = "Marco"

SCOUTS = {
    "worldwide": "Remy",
    "dach": "Nico",
    "benelux-ie": "Lina",
    "nordics": "Esme",
}


def speak(speaker, text):
    speaker = (speaker or "").strip()
    if not speaker:
        return text
    return f"{speaker}  {text}"
