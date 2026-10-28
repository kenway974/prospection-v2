"""Campagne programmée chaque semaine (C77) : prochain passage, à l'heure locale."""

from datetime import datetime, time, timedelta

from prospection.domain.opening import DAYS

WEEKDAYS = DAYS  # lundi = 0


def next_run(now_local: datetime, weekday: int, hour: int) -> datetime:
    """Prochain jour et heure voulus, strictement après `now_local`, dans son fuseau (le
    changement d'heure garde l'heure affichée)."""
    days = (weekday - now_local.weekday()) % 7
    day = now_local.date() + timedelta(days=days)
    candidate = datetime.combine(day, time(hour), tzinfo=now_local.tzinfo)
    return candidate if candidate > now_local else candidate + timedelta(days=7)
