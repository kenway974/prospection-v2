"""Mobile ou fixe ? (C22) — France métropolitaine et outre-mer."""

import phonenumbers

REGIONS = ("FR", "RE", "GP", "MQ", "GF", "YT", "PM", "BL", "MF")
MOBILE_TYPES = {
    phonenumbers.PhoneNumberType.MOBILE,
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
}


def is_mobile(number: str) -> bool:
    """Un numéro national est essayé dans chaque territoire français."""
    for region in REGIONS:
        try:
            parsed = phonenumbers.parse(number, region)
        except phonenumbers.NumberParseException:
            return False
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.number_type(parsed) in MOBILE_TYPES
    return False
