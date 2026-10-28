"""File d'envoi vers le CRM : une ligne par prospect (C67 à C75)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Column,
    Connection,
    DateTime,
    ForeignKey,
    Integer,
    Table,
    Text,
    func,
    select,
    update,
)  # fmt: skip
from sqlalchemy.dialects.postgresql import JSONB, insert

from prospection.domain.call_status import EXPORTED
from prospection.storage.db import metadata
from prospection.storage.schema_campaigns import campaigns, prospects

PENDING, SENT, FAILED = "en attente", "envoyé", "échec"
TS = DateTime(timezone=True)
crm_exports = Table(
    "crm_exports", metadata,
    Column("prospect_id", BigInteger, ForeignKey("prospects.id"), primary_key=True),
    Column("state", Text, nullable=False), Column("outcome", Text), Column("page_id", Text),
    Column("page_url", Text), Column("written_json", JSONB, nullable=False),
    Column("error", Text), Column("attempts", Integer, nullable=False),
    Column("next_try_at", TS, nullable=False), Column("batch_at", TS, nullable=False),
    Column("sent_at", TS),
)  # fmt: skip
_E = crm_exports.c


@dataclass(frozen=True)
class Sent:
    page_id: str | None
    written: dict[str, Any]
    attempts: int


def queue(conn: Connection, ids: list[int], now: datetime) -> None:
    """Met en file (ou remet, pour une mise à jour) ; garde la page et les valeurs envoyées."""
    for pid in ids:
        values = {"state": PENDING, "error": None, "attempts": 0, "next_try_at": now,
                  "batch_at": now, "outcome": None}  # fmt: skip
        statement = insert(crm_exports).values(prospect_id=pid, written_json={}, **values)
        conn.execute(statement.on_conflict_do_update(index_elements=["prospect_id"], set_=values))


def ready(conn: Connection, now: datetime, limit: int) -> list[int]:
    rows = conn.execute(select(_E.prospect_id).where(_E.state == PENDING, _E.next_try_at <= now)
                        .order_by(_E.next_try_at, _E.prospect_id).limit(limit))  # fmt: skip
    return [int(r[0]) for r in rows]


def previous(conn: Connection, prospect_id: int) -> Sent:
    row = conn.execute(select(_E.page_id, _E.written_json, _E.attempts)
                       .where(_E.prospect_id == prospect_id)).one()  # fmt: skip
    return Sent(row.page_id, dict(row.written_json), int(row.attempts))


def mark_sent(
    conn: Connection, prospect_id: int, page: tuple[str, str], written: dict[str, Any],
    outcome: str, now: datetime,
) -> None:  # fmt: skip
    conn.execute(update(crm_exports).where(_E.prospect_id == prospect_id).values(
        state=SENT, outcome=outcome, page_id=page[0], page_url=page[1], written_json=written,
        error=None, sent_at=now))  # fmt: skip
    conn.execute(update(prospects).where(prospects.c.id == prospect_id)
                 .values(status=EXPORTED, updated_at=now))  # fmt: skip


def retry_at(conn: Connection, prospect_id: int, when: datetime, error: str) -> None:
    conn.execute(update(crm_exports).where(_E.prospect_id == prospect_id)
                 .values(next_try_at=when, attempts=_E.attempts + 1, error=error))  # fmt: skip


def mark_failed(conn: Connection, prospect_id: int, error: str) -> None:
    conn.execute(update(crm_exports).where(_E.prospect_id == prospect_id)
                 .values(state=FAILED, error=error[:500]))  # fmt: skip


def last_batch(conn: Connection) -> list[tuple[str, str, str | None, str | None]]:
    """Dernier envoi demandé : (entreprise, état, résultat, erreur) de chaque prospect."""
    latest = select(func.max(_E.batch_at)).scalar_subquery()
    rows = conn.execute(
        select(prospects.c.data_json["name"].astext, _E.state, _E.outcome, _E.error)
        .join(prospects, prospects.c.id == _E.prospect_id).where(_E.batch_at == latest)
    )  # fmt: skip
    return [(str(r[0]), str(r[1]), r[2], r[3]) for r in rows]


def crm_link(conn: Connection, prospect_id: int) -> str | None:
    found = conn.execute(select(_E.page_url).where(_E.prospect_id == prospect_id,
                                                   _E.page_url.is_not(None))).first()  # fmt: skip
    return str(found[0]) if found else None


def campaign_name(conn: Connection, prospect_id: int) -> str:
    row = conn.execute(
        select(campaigns.c.name)
        .join(prospects, prospects.c.campaign_id == campaigns.c.id)
        .where(prospects.c.id == prospect_id)
    ).first()  # fmt: skip
    return str(row[0]) if row and row[0] else ""


def waiting(conn: Connection) -> int:
    return int(conn.execute(select(func.count()).where(_E.state == PENDING)).scalar_one())
