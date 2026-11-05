"""Réglages du mail d'audit et compte Gmail relié (ligne unique ; jeton chiffré) (C144)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Connection,
    DateTime,
    LargeBinary,
    SmallInteger,
    Table,
    Text,
    select,
    update,
)

from prospection.domain.mail_settings import MailSettings
from prospection.storage.db import metadata

mail_settings = Table(
    "mail_settings", metadata,
    Column("id", SmallInteger, primary_key=True),
    Column("sender_name", Text), Column("phone", Text), Column("portfolio", Text),
    Column("calendly", Text),
    Column("reminder_days", SmallInteger, nullable=False, server_default="2"),
    Column("gmail_address", Text), Column("gmail_token", LargeBinary),
    Column("gmail_connected_at", DateTime(timezone=True)),
    CheckConstraint("id = 1", name="mail_settings_single_row"),
)  # fmt: skip
_ROW = mail_settings.c.id == 1


@dataclass(frozen=True)
class GmailAccount:
    address: str
    token: bytes  # jeton de connexion chiffré (SecretBox)
    connected_at: datetime


def load_mail_settings(conn: Connection) -> MailSettings:
    m = mail_settings.c
    row = conn.execute(
        select(m.sender_name, m.phone, m.portfolio, m.calendly, m.reminder_days).where(_ROW)
    ).one()
    return MailSettings(row.sender_name, row.phone, row.portfolio, row.calendly,
                        row.reminder_days)  # fmt: skip


def save_mail_settings(conn: Connection, s: MailSettings) -> None:
    conn.execute(update(mail_settings).where(_ROW).values(
        sender_name=s.sender_name, phone=s.phone, portfolio=s.portfolio, calendly=s.calendly,
        reminder_days=s.reminder_days))  # fmt: skip


def load_gmail(conn: Connection) -> GmailAccount | None:
    m = mail_settings.c
    row = conn.execute(
        select(m.gmail_address, m.gmail_token, m.gmail_connected_at).where(_ROW)
    ).one()
    if not (row.gmail_address and row.gmail_token and row.gmail_connected_at):
        return None
    return GmailAccount(row.gmail_address, bytes(row.gmail_token), row.gmail_connected_at)


def save_gmail(
    conn: Connection, address: str | None, token: bytes | None, now: datetime | None
) -> None:
    """Relie (adresse, jeton chiffré, date) ou délie (tout à None) le compte Gmail."""
    conn.execute(update(mail_settings).where(_ROW).values(
        gmail_address=address, gmail_token=token, gmail_connected_at=now))  # fmt: skip
