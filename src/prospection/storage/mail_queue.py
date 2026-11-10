"""File d'envoi groupé du mail d'audit (C168 à C170) : une ligne par prospect et par envoi."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Connection,
    DateTime,
    ForeignKey,
    SmallInteger,
    Table,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.db import metadata

WAITING, SENT, FAILED, SKIPPED, CANCELLED = "attente", "envoye", "echec", "ecarte", "annule"
TS = DateTime(timezone=True)
mail_queue = Table(
    "mail_queue", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("prospect_id", BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"),
           nullable=False),
    Column("queued_at", TS, nullable=False),
    Column("status", Text, nullable=False, server_default=WAITING),
    Column("reason", Text), Column("done_at", TS), Column("gap_seconds", SmallInteger),
    CheckConstraint("status IN ('attente', 'envoye', 'echec', 'ecarte', 'annule')",
                    name="mail_queue_status"),
)  # fmt: skip
_Q = mail_queue.c


def enqueue(conn: Connection, prospect_ids: Sequence[int], now: datetime) -> int:
    """Met en file ; un prospect déjà en attente n'est pas ajouté deux fois."""
    if not prospect_ids:
        return 0
    rows = [{"prospect_id": i, "queued_at": now} for i in prospect_ids]
    added = conn.execute(
        insert(mail_queue)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["prospect_id"], index_where=_Q.status == WAITING)
        .returning(_Q.id)
    )
    return len(added.all())


def pending_ids(conn: Connection) -> list[int]:
    """Prospects en attente, dans l'ordre d'arrivée."""
    found = select(_Q.prospect_id).where(_Q.status == WAITING).order_by(_Q.queued_at, _Q.id)
    return list(conn.execute(found).scalars())


def waiting_among(conn: Connection, prospect_ids: Sequence[int]) -> set[int]:
    found = select(_Q.prospect_id).where(_Q.status == WAITING, _Q.prospect_id.in_(prospect_ids))
    return set(conn.execute(found).scalars())
