"""Libellé de l'état du contact d'un prospect sur la liste (C184)."""

from datetime import datetime
from zoneinfo import ZoneInfo

MAILED = frozenset({"envoye", "refuse", "file", "sms"})  # déjà contacté (mail ou SMS)
_WORDS = {"envoye": "Mail envoyé le", "refuse": "Mail refusé le", "sms": "SMS envoyé le"}


def contact_label(kind: str, at: datetime | None, timezone: str) -> str:
    if kind == "file" or at is None:
        return "En file d'envoi"
    return f"{_WORDS[kind]} {at.astimezone(ZoneInfo(timezone)).strftime('%d/%m')}"
