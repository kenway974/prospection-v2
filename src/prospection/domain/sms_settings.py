"""Réglages des SMS (C175) : activés ou non, nom d'expéditeur, plafond par jour."""

import re
from dataclasses import dataclass

MAX_LIMIT = 200
_SENDER = re.compile(r"[A-Za-z0-9]{3,11}")  # nom alphanumérique des opérateurs français


@dataclass(frozen=True)
class SmsSettings:
    enabled: bool
    sender: str
    daily_limit: int


class InvalidSmsSettings(ValueError):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Réglages des SMS refusés")
        self.errors = errors


def clean_sms_settings(enabled: str, sender: str, limit: str) -> SmsSettings:
    """InvalidSmsSettings (champ → message qui dit quoi faire) si une saisie est refusée."""
    errors: dict[str, str] = {}
    name = sender.strip()
    if not _SENDER.fullmatch(name) or name.isdigit():
        errors["sender"] = "Nom d'expéditeur : 3 à 11 lettres ou chiffres, sans espace (ex. Kenny)."
    try:
        daily = int(limit.strip())
    except ValueError:
        daily = 0
    if not 1 <= daily <= MAX_LIMIT:
        errors["limit"] = f"Indiquez un nombre de SMS par jour entre 1 et {MAX_LIMIT}."
    if errors:
        raise InvalidSmsSettings(errors)
    return SmsSettings(enabled == "on", name, daily)
