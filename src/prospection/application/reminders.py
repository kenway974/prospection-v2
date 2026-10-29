"""Rappels avant chaque relance (C108) : une alerte par action, au bon moment."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from prospection.domain.call_status import ACTION_KINDS
from prospection.domain.reminders import reminder_due
from prospection.storage.alerts import add_alert, retire_alerts
from prospection.storage.app_settings import load_app_settings, save_reminders
from prospection.storage.call_tracking import agenda_items

MINUTES_RANGE, HOURS_RANGE = range(0, 241), range(0, 24)


class InvalidReminders(ValueError):
    """Réglage hors limites ; le message dit quoi faire."""


def remind_due_actions(engine: Engine, now: datetime, timezone: str) -> int:
    """Crée les alertes dues ; renvoie combien de nouvelles."""
    local = now.astimezone(ZoneInfo(timezone))
    created, current = 0, set()
    with engine.begin() as conn:
        settings = load_app_settings(conn)
        for item in agenda_items(conn):
            key = f"relance:{item.id}:{item.due_date}:{item.due_time}"
            current.add(key)
            due = reminder_due(item.due_date, item.due_time, local, settings.reminder_minutes,
                               settings.reminder_hour)  # fmt: skip
            if not due:
                continue
            when = item.due_time.strftime("%H:%M") if item.due_time else "aujourd'hui"
            kind = ACTION_KINDS.get(item.kind, item.kind)
            message = f"{kind} · {item.prospect_name} · {when}"
            created += add_alert(conn, key, "relance", message, f"/prospects/{item.prospect_id}",
                                 now)  # fmt: skip
        retire_alerts(conn, "relance:", current, now)  # action déplacée ou terminée
    return created


def _number(text: str) -> int:
    clean = text.strip()
    return int(clean) if clean.isascii() and clean.isdigit() else -1


def change_reminders(
    engine: Engine, minutes: str, hour: str, quiet_start: str = "21", quiet_end: str = "8"
) -> None:
    """Délais des rappels et heures calmes des notifications (début = fin : aucune)."""
    lead, morning = _number(minutes), _number(hour)
    calm = (_number(quiet_start), _number(quiet_end))
    if lead not in MINUTES_RANGE:
        raise InvalidReminders("Choisissez entre 0 et 240 minutes.")
    if morning not in HOURS_RANGE or not all(h in HOURS_RANGE for h in calm):
        raise InvalidReminders("Choisissez une heure entre 0 et 23.")
    with engine.begin() as conn:
        save_reminders(conn, lead, morning, *calm)
