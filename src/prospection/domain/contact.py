"""Contact saisi sur la fiche : dirigeant, mobile, email (C105)."""

import phonenumbers

from prospection.domain.email_check import is_email
from prospection.domain.phones import parse_phone

BAD_PHONE = "Numéro invalide : vérifiez-le, ou écrivez-le avec l'indicatif (+33…)."
BAD_EMAIL = "Adresse email invalide : vérifiez-la."


class InvalidContact(ValueError):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Contact invalide")
        self.errors = errors


def _phone(text: str, country: str) -> str | None:
    parsed = parse_phone(text, country)
    return (
        phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164) if parsed else None
    )


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
    if clean_email and not is_email(clean_email):
        errors["email"] = BAD_EMAIL
    if errors:
        raise InvalidContact(errors)
    return clean_name, clean_mobile, clean_email
