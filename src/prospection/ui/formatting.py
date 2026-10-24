"""Formats de dates en français, dans le fuseau du propriétaire."""

from datetime import datetime
from zoneinfo import ZoneInfo

DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MONTHS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def long_day(moment: datetime, timezone: str) -> str:
    """Ex. « dimanche 25 octobre »."""
    local = moment.astimezone(ZoneInfo(timezone))
    return f"{DAYS[local.weekday()]} {local.day} {MONTHS[local.month - 1]}"


def short_datetime(moment: datetime, timezone: str) -> str:
    """Ex. « 24/10/2026 13:00 »."""
    return moment.astimezone(ZoneInfo(timezone)).strftime("%d/%m/%Y %H:%M")
