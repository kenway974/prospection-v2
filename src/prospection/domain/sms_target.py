"""Numéro qui peut recevoir le SMS (C176) : un mobile français (06, 07, +33 6, +33 7)."""

from collections.abc import Iterable

import phonenumbers


def french_mobile(numbers: Iterable[str]) -> str | None:
    """Premier mobile français, au format international (+336…), sinon None."""
    for number in numbers:
        try:
            parsed = phonenumbers.parse(number, "FR")
        except phonenumbers.NumberParseException:
            continue
        mobile = phonenumbers.number_type(parsed) == phonenumbers.PhoneNumberType.MOBILE
        if mobile and phonenumbers.region_code_for_number(parsed) == "FR":
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    return None
