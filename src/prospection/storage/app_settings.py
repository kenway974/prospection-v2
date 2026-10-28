"""Réglages de l'app : CRM, base Notion, budget Google (ligne unique)."""

from dataclasses import dataclass

from sqlalchemy import Connection, select, update

from prospection.domain.crm_choice import Crm
from prospection.storage.db import app_settings


@dataclass(frozen=True)
class AppSettings:
    crm: Crm
    notion_database_id: str | None
    notion_database_title: str | None
    google_budget_cents: int | None
    reminder_minutes: int = 15  # C108 : avant une action avec heure
    reminder_hour: int = 8  # C108 : pour celles du jour sans heure
    purge_months: int = 6  # C94 : purge des prospects non retenus sans activité


def load_app_settings(conn: Connection) -> AppSettings:
    row = conn.execute(select(app_settings).where(app_settings.c.id == 1)).one()
    return AppSettings(
        Crm(row.crm), row.notion_database_id, row.notion_database_title, row.google_budget_cents,
        row.reminder_minutes, row.reminder_hour, row.purge_months,
    )  # fmt: skip


def save_crm(
    conn: Connection, crm: Crm, database_id: str | None, database_title: str | None
) -> None:
    conn.execute(
        update(app_settings)
        .where(app_settings.c.id == 1)
        .values(crm=crm.value, notion_database_id=database_id, notion_database_title=database_title)
    )


def save_budget(conn: Connection, cents: int) -> None:
    conn.execute(
        update(app_settings).where(app_settings.c.id == 1).values(google_budget_cents=cents)
    )


def save_reminders(conn: Connection, minutes: int, hour: int) -> None:
    conn.execute(
        update(app_settings)
        .where(app_settings.c.id == 1)
        .values(reminder_minutes=minutes, reminder_hour=hour)
    )


def save_purge_months(conn: Connection, months: int) -> None:
    conn.execute(update(app_settings).where(app_settings.c.id == 1).values(purge_months=months))
