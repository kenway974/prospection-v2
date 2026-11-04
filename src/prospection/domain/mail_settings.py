"""Réglages du mail d'audit : expéditeur, liens, délai du rappel (C144)."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from prospection.domain.audit_mail import MailSender
from prospection.domain.place import web_link
from prospection.domain.text import without_controls

MIN_DAYS, MAX_DAYS, DEFAULT_DAYS = 1, 3, 2


class InvalidMailSettings(ValueError):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Réglages du mail invalides")
        self.errors = errors


@dataclass(frozen=True)
class MailSettings:
    sender_name: str | None
    phone: str | None
    portfolio: str | None
    calendly: str | None
    reminder_days: int = DEFAULT_DAYS


def _https(url: str) -> str | None:
    link = web_link(url.strip())
    return link if link and urlsplit(link).scheme == "https" else None


def clean_mail_settings(
    name: str, phone: str, portfolio: str, calendly: str, days: str
) -> MailSettings:
    errors: dict[str, str] = {}
    clean_name = " ".join(without_controls(name).split())
    if not 2 <= len(clean_name) <= 80:
        errors["name"] = "Écrivez votre nom (2 à 80 caractères) : il signe le mail."
    clean_phone = " ".join(without_controls(phone).split()) or None
    if clean_phone and len(clean_phone) > 30:
        errors["phone"] = "Numéro trop long : 30 caractères au plus."
    clean_portfolio = _https(portfolio)
    if clean_portfolio is None:
        errors["portfolio"] = "Collez l'adresse complète du portfolio (https://…)."
    clean_calendly = _https(calendly) if calendly.strip() else None
    if calendly.strip() and clean_calendly is None:
        errors["calendly"] = (
            "Collez l'adresse complète du lien Calendly (https://…), ou laissez vide."
        )
    reminder = int(days) if days.strip().isdigit() else 0
    if not MIN_DAYS <= reminder <= MAX_DAYS:
        errors["days"] = "Choisissez un rappel dans 1, 2 ou 3 jours."
    if errors:
        raise InvalidMailSettings(errors)
    return MailSettings(clean_name, clean_phone, clean_portfolio, clean_calendly, reminder)


def sender_of(settings: MailSettings) -> MailSender | None:
    """Expéditeur du mail ; None tant que le nom ou le portfolio manquent."""
    if not settings.sender_name or not settings.portfolio:
        return None
    return MailSender(settings.sender_name, settings.phone, settings.portfolio, settings.calendly)
