"""Mobile ou fixe ? (C22, C124) — France, outre-mer, Belgique, Suisse, Luxembourg, Monaco."""

import phonenumbers

REGIONS = ("FR", "RE", "GP", "MQ", "GF", "YT", "PM", "BL", "MF")
MOBILE_TYPES = {
    phonenumbers.PhoneNumberType.MOBILE,
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
}


def is_mobile(number: str, country: str | None = None) -> bool:
    """Un numéro international se suffit ; un numéro national est lu dans le pays de
    l'établissement s'il est connu, sinon dans chaque territoire français."""
    regions = (country,) if country and country != "FR" else REGIONS
    for region in regions:
        try:
            parsed = phonenumbers.parse(number, region)
        except phonenumbers.NumberParseException:
            return False
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.number_type(parsed) in MOBILE_TYPES
    return False
