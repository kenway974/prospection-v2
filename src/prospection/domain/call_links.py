"""Pour appeler : type de numéro (C55) et recherche LinkedIn du dirigeant (C56).

LinkedIn n'est jamais lu (règle 2) : on construit seulement un lien de recherche que le
propriétaire ouvre lui-même. Repris de prospection-bot (services/linkedin.py,
people_search_url, version 530ba12).
"""

from urllib.parse import urlencode

import phonenumbers

from prospection.domain.phones import MOBILE_TYPES, parse_phone

SEARCH_URL = "https://www.linkedin.com/search/results/people/"
DEFAULT_ROLE = "gérant"


def phone_kind(number: str, country: str | None) -> str:
    """« mobile », « fixe », ou « inconnu » si le numéro ne se lit pas."""
    parsed = parse_phone(number, country)
    if parsed is None:
        return "inconnu"
    return "mobile" if phonenumbers.number_type(parsed) in MOBILE_TYPES else "fixe"


def normalized(number: str, country: str | None) -> str:
    """Forme internationale pour reconnaître un même numéro écrit autrement."""
    parsed = parse_phone(number, country)
    return (
        phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        if parsed
        else number
    )


def national(number: str, country: str | None) -> str:
    """Forme lisible (« 06 12 34 56 78 ») ; telle quelle si elle ne se lit pas."""
    parsed = parse_phone(number, country)
    return (
        phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        if parsed
        else number
    )


def leader_name(leaders: tuple[str, ...]) -> str | None:
    """Premier dirigeant, sans sa fonction (« Marie DUPONT (Présidente) » → « Marie DUPONT »)."""
    if not leaders:
        return None
    return leaders[0].split(" (", 1)[0].strip() or None


def linkedin_search(person: str | None, company: str) -> str:
    """Lien de recherche des personnes : le dirigeant s'il est connu, sinon le rôle."""
    who = (person or DEFAULT_ROLE).strip()[:100]
    return f"{SEARCH_URL}?{urlencode({'keywords': f'{who} {company.strip()[:100]}'})}"
