"""« Ouvert maintenant ? » lu dans les horaires de la fiche Google (C113), sans appel payant.

Horaires en français (« lundi: 08:00-12:00, 14:00-18:00 », tiret long de Google compris,
« Fermé », « Ouvert 24h/24 »).
Inconnu (jour absent, format imprévu) : None, jamais deviné.
"""

import re
from datetime import datetime, time

DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_SLOT = re.compile(r"(\d{1,2})[:h](\d{2})\s*[\u2013-]\s*(\d{1,2})[:h](\d{2})")


def _slots(text: str) -> list[tuple[time, time]] | None:
    found = _SLOT.findall(text)
    if not found:
        return None
    slots = []
    for h1, m1, h2, m2 in found:
        end = time(23, 59) if int(h2) >= 24 else time(int(h2), int(m2))
        slots.append((time(int(h1) % 24, int(m1)), end))
    return slots


def open_now(hours: tuple[str, ...], now: datetime) -> bool | None:
    """`now` : heure locale du commerce (fuseau du propriétaire)."""
    day = DAYS[now.weekday()]
    line = next((h for h in hours if h.lower().startswith(day)), None)
    if line is None:
        return None
    text = line.split(":", 1)[1].strip().lower() if ":" in line else ""
    if "fermé" in text:
        return False
    if "24h/24" in text or "24 h/24" in text:
        return True
    slots = _slots(text)
    if slots is None:
        return None
    current = now.time()
    return any(start <= current < end if start <= end else (current >= start or current < end)
               for start, end in slots)  # fmt: skip
