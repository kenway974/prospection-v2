"""Réglages des SMS (ligne unique) (C175)."""

from sqlalchemy import Connection, select, update

from prospection.domain.sms_settings import SmsSettings
from prospection.storage.sms_tables import sms_settings

_ROW = sms_settings.c.id == 1


def load_sms_settings(conn: Connection) -> SmsSettings:
    s = sms_settings.c
    row = conn.execute(select(s.enabled, s.sender, s.daily_limit).where(_ROW)).one()
    return SmsSettings(bool(row.enabled), str(row.sender), int(row.daily_limit))


def save_sms_settings(conn: Connection, settings: SmsSettings) -> None:
    values = {"enabled": settings.enabled, "sender": settings.sender,
              "daily_limit": settings.daily_limit}  # fmt: skip
    conn.execute(update(sms_settings).where(_ROW).values(**values))
