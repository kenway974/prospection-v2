"""Consommation Google du mois (C07) : compteur global, protégé par un verrou."""

from sqlalchemy import Connection, select, text
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.schema_campaigns import google_usage

GOOGLE_LOCK_KEY = 9740002


def lock_google(conn: Connection) -> None:
    """Un seul appel Google « réservé » à la fois jusqu'à la fin de la transaction."""
    conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": GOOGLE_LOCK_KEY})


def month_usage(conn: Connection, month: str) -> tuple[int, int]:
    """(appels, centimes dépensés) pour le mois « AAAA-MM »."""
    g = google_usage.c
    row = conn.execute(select(g.calls, g.cost_cents).where(g.month == month)).first()
    return (row.calls, row.cost_cents) if row else (0, 0)


def add_call(conn: Connection, month: str, cost_cents: int) -> None:
    g = google_usage.c
    statement = insert(google_usage).values(month=month, calls=1, cost_cents=cost_cents)
    conn.execute(
        statement.on_conflict_do_update(
            index_elements=["month"],
            set_={"calls": g.calls + 1, "cost_cents": g.cost_cents + cost_cents},
        )
    )
