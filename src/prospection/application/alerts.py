"""Alertes affichées sur l'écran Aujourd'hui (C78, C98, C108)."""

from datetime import datetime

from sqlalchemy import Engine

from prospection.storage.alerts import Alert, mark_seen, unseen_alerts
from prospection.storage.app_settings import load_app_settings


def current_alerts(engine: Engine) -> list[Alert]:
    with engine.connect() as conn:
        return unseen_alerts(conn)


def dismiss(engine: Engine, now: datetime, alert_id: int | None = None) -> None:
    """Une alerte, ou toutes."""
    with engine.begin() as conn:
        mark_seen(conn, now, alert_id)


def reminder_settings(engine: Engine) -> tuple[int, int]:
    with engine.connect() as conn:
        settings = load_app_settings(conn)
    return settings.reminder_minutes, settings.reminder_hour
