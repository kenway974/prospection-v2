"""Mobile ou fixe ? (C22, C124) — France, outre-mer, Belgique, Suisse, Luxembourg, Monaco."""

import phonenumbers

from prospection.domain.territories import FRENCH_TERRITORIES

REGIONS = FRENCH_TERRITORIES
MOBILE_TYPES = {
    phonenumbers.PhoneNumberType.MOBILE,
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
}


def parse_phone(number: str, country: str | None = None) -> phonenumbers.PhoneNumber | None:
    """Lecture unique d'un numéro : international tel quel ; national lu dans le pays de
    l'établissement, puis dans chaque territoire français (0692… à La Réunion)."""
    for region in dict.fromkeys((country or "FR", *REGIONS)):
        try:
            parsed = phonenumbers.parse(number, region)
        except phonenumbers.NumberParseException:
            continue
        if phonenumbers.is_valid_number(parsed):
            return parsed
    return None


def is_mobile(number: str, country: str | None = None) -> bool:
    parsed = parse_phone(number, country)
    return parsed is not None and phonenumbers.number_type(parsed) in MOBILE_TYPES
