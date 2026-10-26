"""Contact saisi sur la fiche : dirigeant, mobile, email (C105)."""

import re

import phonenumbers

_EMAIL = re.compile(r"[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}")
BAD_PHONE = "Numéro invalide : vérifiez-le, ou écrivez-le avec l'indicatif (+33…)."
BAD_EMAIL = "Adresse email invalide : vérifiez-la."


class InvalidContact(ValueError):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Contact invalide")
        self.errors = errors


def _phone(text: str, country: str) -> str | None:
    try:
        parsed = phonenumbers.parse(text, country)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def clean_contact(
    name: str, mobile: str, email: str, country: str
) -> tuple[str | None, str | None, str | None]:
    """Champs vides = rien ; mobile au format international ; email en minuscules."""
    errors: dict[str, str] = {}
    clean_name = " ".join(name.split()) or None
    if clean_name and len(clean_name) > 100:
        errors["name"] = "100 caractères au plus : raccourcissez le nom."
    clean_mobile = None
    if mobile.strip():
        clean_mobile = _phone(mobile.strip(), country) if len(mobile.strip()) <= 30 else None
        if clean_mobile is None:
            errors["mobile"] = BAD_PHONE
    clean_email = email.strip().lower() or None
    if clean_email and (len(clean_email) > 254 or not _EMAIL.fullmatch(clean_email)):
        errors["email"] = BAD_EMAIL
    if errors:
        raise InvalidContact(errors)
    return clean_name, clean_mobile, clean_email
