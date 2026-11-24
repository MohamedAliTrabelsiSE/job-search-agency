"""Which scouts run is a function of the interest saved at onboarding."""

REGIONS = {
    "germany": "dach",
    "austria": "dach",
    "netherlands": "benelux-ie",
    "belgium": "benelux-ie",
    "ireland": "benelux-ie",
    "sweden": "nordics",
    "denmark": "nordics",
    "finland": "nordics",
    "norway": "nordics",
}


def scouts_for(preferences):
    interest = (preferences.get("interest") or "").lower()
    names = []
    if interest in ("remote", "both"):
        names.append("worldwide")
    if interest in ("relocate", "both"):
        for place in preferences.get("places") or []:
            region = REGIONS.get(str(place).lower())
            if region and region not in names:
                names.append(region)
    return names
