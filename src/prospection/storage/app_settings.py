"""Réglages de l'app : CRM, base Notion, budget Google (ligne unique)."""

from dataclasses import dataclass

from sqlalchemy import Connection, select, update

from prospection.domain.crm_choice import Crm
from prospection.storage.db import app_settings

__all__ = ["AppSettings", "Crm", "load_app_settings", "save_budget", "save_crm"]


@dataclass(frozen=True)
class AppSettings:
    crm: Crm
    notion_database_id: str | None
    notion_database_title: str | None
    google_budget_cents: int | None


def load_app_settings(conn: Connection) -> AppSettings:
    row = conn.execute(select(app_settings).where(app_settings.c.id == 1)).one()
    return AppSettings(
        Crm(row.crm), row.notion_database_id, row.notion_database_title, row.google_budget_cents
    )


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
