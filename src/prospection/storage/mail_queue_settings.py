"""Réglages de l'envoi groupé (C169, C170) : plafond par jour, file arrêtée (et pourquoi)."""

from sqlalchemy import Connection, select, update

from prospection.storage.mail_settings import mail_settings

_ROW = mail_settings.c.id == 1


def daily_limit(conn: Connection) -> int:
    return int(conn.execute(select(mail_settings.c.daily_limit).where(_ROW)).scalar_one())


def save_daily_limit(conn: Connection, limit: int) -> None:
    conn.execute(update(mail_settings).where(_ROW).values(daily_limit=limit))


def paused(conn: Connection) -> str | None:
    return conn.execute(select(mail_settings.c.queue_paused).where(_ROW)).scalar()


def set_paused(conn: Connection, reason: str | None) -> None:
    conn.execute(update(mail_settings).where(_ROW).values(queue_paused=reason))
