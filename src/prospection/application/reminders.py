"""Rappels avant chaque relance (C108) : une alerte par action, au bon moment."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from prospection.domain.call_status import ACTION_KINDS
from prospection.domain.reminders import reminder_due
from prospection.storage.alerts import add_alert
from prospection.storage.app_settings import load_app_settings, save_reminders
from prospection.storage.call_tracking import agenda_items

MINUTES_RANGE, HOURS_RANGE = range(0, 241), range(0, 24)


class InvalidReminders(ValueError):
    """Réglage hors limites ; le message dit quoi faire."""


def remind_due_actions(engine: Engine, now: datetime, timezone: str) -> int:
    """Crée les alertes dues ; renvoie combien de nouvelles."""
    local = now.astimezone(ZoneInfo(timezone))
    created = 0
    with engine.begin() as conn:
        settings = load_app_settings(conn)
        for item in agenda_items(conn):
            due = reminder_due(item.due_date, item.due_time, local, settings.reminder_minutes,
                               settings.reminder_hour)  # fmt: skip
            if not due:
                continue
            when = item.due_time.strftime("%H:%M") if item.due_time else "aujourd'hui"
            kind = ACTION_KINDS.get(item.kind, item.kind)
            key = f"relance:{item.id}:{item.due_date}:{item.due_time}"
            message = f"{kind} · {item.prospect_name} · {when}"
            created += add_alert(conn, key, "relance", message, f"/prospects/{item.prospect_id}",
                                 now)  # fmt: skip
    return created


def change_reminders(engine: Engine, minutes: str, hour: str) -> None:
    lead = int(minutes) if minutes.strip().isdigit() else -1
    morning = int(hour) if hour.strip().isdigit() else -1
    if lead not in MINUTES_RANGE:
        raise InvalidReminders("Choisissez entre 0 et 240 minutes.")
    if morning not in HOURS_RANGE:
        raise InvalidReminders("Choisissez une heure entre 0 et 23.")
    with engine.begin() as conn:
        save_reminders(conn, lead, morning)
