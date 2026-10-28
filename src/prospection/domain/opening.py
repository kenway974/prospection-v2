"""« Ouvert maintenant ? » lu dans les horaires de la fiche Google (C113), sans appel payant.

Horaires en français (« lundi: 08:00-12:00, 14:00-18:00 », tiret long de Google compris,
« Fermé », « Ouvert 24h/24 »).
Inconnu (jour absent, format imprévu) : None, jamais deviné.
"""

import re
from datetime import datetime

DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_SLOT = re.compile(r"(\d{1,2})[:h](\d{2})\s*[\u2013-]\s*(\d{1,2})[:h](\d{2})")


def _day(hours: tuple[str, ...], day: str) -> list[tuple[int, int]] | None:
    """Créneaux du jour en minutes depuis minuit (fin au-delà de 1440 si le créneau passe
    minuit) ; [] si fermé ; None si inconnu."""
    line = next((h for h in hours if h.lower().startswith(day)), None)
    if line is None:
        return None
    text = line.split(":", 1)[1].strip().lower() if ":" in line else ""
    if "fermé" in text:
        return []
    if "24h/24" in text or "24 h/24" in text:
        return [(0, 1440)]
    found = _SLOT.findall(text)
    if not found:
        return None
    slots = []
    for h1, m1, h2, m2 in found:
        start, end = int(h1) % 24 * 60 + int(m1), int(h2) * 60 + int(m2)
        slots.append((start, end + 1440 if end <= start else end))
    return slots


def open_now(hours: tuple[str, ...], now: datetime) -> bool | None:
    """`now` : heure locale du commerce (fuseau du propriétaire). La veille compte pour un
    créneau qui passe minuit (« dimanche: 18:00-02:00 » : ouvert lundi à 1 h)."""
    today = _day(hours, DAYS[now.weekday()])
    if today is None:
        return None
    minute = now.hour * 60 + now.minute
    if any(start <= minute < end for start, end in today):
        return True
    yesterday = _day(hours, DAYS[now.weekday() - 1]) or []
    return any(minute + 1440 < end for _, end in yesterday)
