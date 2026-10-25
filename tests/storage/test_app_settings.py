"""C05, C06, C07 : réglages de l'app (ligne unique)."""

from sqlalchemy import Connection

from prospection.storage.app_settings import (
    AppSettings,
    Crm,
    load_app_settings,
    save_budget,
    save_crm,
)


def test_defaults(conn: Connection) -> None:
    assert load_app_settings(conn) == AppSettings(Crm.NONE, None, None, None)


def test_C05_C06_crm_saved(conn: Connection) -> None:
    save_crm(conn, Crm.NOTION, "db-1", "Prospects v2")
    assert load_app_settings(conn) == AppSettings(Crm.NOTION, "db-1", "Prospects v2", None)
    save_crm(conn, Crm.NONE, None, None)
    assert load_app_settings(conn).crm is Crm.NONE


def test_C07_budget_saved(conn: Connection) -> None:
    save_budget(conn, 2500)
    assert load_app_settings(conn).google_budget_cents == 2500
