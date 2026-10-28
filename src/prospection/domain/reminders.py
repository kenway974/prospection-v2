"""Quand prévenir d'une relance (C108) : 15 min avant une action avec heure, à 8 h pour
celles du jour sans heure ; les deux réglables. L'heure locale est passée en paramètre."""

from datetime import date, datetime, time, timedelta

STILL_USEFUL = timedelta(hours=2)  # tâche de fond arrêtée un moment : le rappel sert encore


def reminder_due(
    due_date: date, due_time: time | None, now_local: datetime, lead_minutes: int = 15,
    morning_hour: int = 8,
) -> bool:  # fmt: skip
    if due_time is None:
        return due_date == now_local.date() and now_local.hour >= morning_hour
    due = datetime.combine(due_date, due_time, tzinfo=now_local.tzinfo)
    return due - timedelta(minutes=lead_minutes) <= now_local < due + STILL_USEFUL
