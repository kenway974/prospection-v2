"""Rythme de l'envoi groupé du mail d'audit (C169) : du lundi au vendredi hors jours fériés
français, de 9 h à 19 h (heure locale), 60 à 120 secondes tirées au hasard entre deux envois,
plafond par jour.

Règle pure : l'heure, le dernier envoi et le compte du jour sont passés en paramètres.
"""

import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

GAP_MIN, GAP_MAX = 60, 120  # secondes : un envoi régulier ressemble à un robot
OPEN_HOUR, CLOSE_HOUR = 9, 19
WORKING_DAYS = range(5)  # lundi à vendredi


FIXED_HOLIDAYS = ((1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25))
EASTER_OFFSETS = (1, 39, 50)  # lundi de Pâques, Ascension, lundi de Pentecôte


def _easter(year: int) -> date:
    """Dimanche de Pâques (calendrier grégorien, algorithme de Meeus)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def is_holiday(day: date) -> bool:
    easter = _easter(day.year)
    moving = {easter + timedelta(days=offset) for offset in EASTER_OFFSETS}
    return (day.month, day.day) in FIXED_HOLIDAYS or day in moving


def in_hours(now: datetime, timezone: str) -> bool:
    local = now.astimezone(ZoneInfo(timezone))
    open_day = local.weekday() in WORKING_DAYS and not is_holiday(local.date())
    return open_day and OPEN_HOUR <= local.hour < CLOSE_HOUR


def may_send(
    now: datetime, last: tuple[datetime, int] | None, sent_today: int, limit: int,
    timezone: str,
) -> bool:  # fmt: skip
    """`last` : heure du dernier envoi et attente tirée après lui (secondes)."""
    if not in_hours(now, timezone) or sent_today >= limit:
        return False
    return last is None or now >= last[0] + timedelta(seconds=last[1])


def next_gap(rng: random.Random) -> int:
    return rng.randint(GAP_MIN, GAP_MAX)


def local_day_start(now: datetime, timezone: str) -> datetime:
    """Début du jour local, pour compter les envois du jour."""
    local = now.astimezone(ZoneInfo(timezone))
    return local.replace(hour=0, minute=0, second=0, microsecond=0)
