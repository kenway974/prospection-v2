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
    func,
    select,
    update,
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


def next_waiting(conn: Connection) -> tuple[int, int] | None:
    """Ligne et prospect les plus anciens en attente."""
    found = select(_Q.id, _Q.prospect_id).where(_Q.status == WAITING)
    row = conn.execute(found.order_by(_Q.queued_at, _Q.id).limit(1)).first()
    return (int(row.id), int(row.prospect_id)) if row else None


def last_attempt(conn: Connection) -> tuple[datetime, int] | None:
    """Dernier passage par Gmail et l'attente tirée après lui (C169)."""
    found = select(_Q.done_at, _Q.gap_seconds).where(_Q.gap_seconds.is_not(None))
    row = conn.execute(found.order_by(_Q.done_at.desc()).limit(1)).first()
    return (row.done_at, int(row.gap_seconds)) if row else None


def sent_since(conn: Connection, start: datetime) -> int:
    found = select(func.count()).where(_Q.status == SENT, _Q.done_at >= start)
    return int(conn.execute(found).scalar_one())


def finish(
    conn: Connection, queue_id: int, status: str, reason: str | None, now: datetime,
    gap: int | None,
) -> None:  # fmt: skip
    """`gap` : attente avant l'envoi suivant ; None quand Gmail n'a pas été appelé."""
    conn.execute(update(mail_queue).where(_Q.id == queue_id).values(
        status=status, reason=reason, done_at=now, gap_seconds=gap))  # fmt: skip


def last_attempts(conn: Connection, count: int) -> list[str]:
    """Statuts des derniers passages par Gmail, le plus récent d'abord (C170)."""
    found = select(_Q.status).where(_Q.gap_seconds.is_not(None)).order_by(_Q.done_at.desc())
    return list(conn.execute(found.limit(count)).scalars())


def recent(conn: Connection, limit: int) -> list[tuple[int, str, str, str | None, datetime]]:
    """Lignes à montrer (C170) : en attente d'abord, puis les dernières traitées."""
    from prospection.storage.schema_campaigns import prospects

    name = prospects.c.data_json["name"].astext
    waiting_first = (_Q.status != WAITING).asc()
    found = (
        select(_Q.id, name.label("name"), _Q.status, _Q.reason,
               func.coalesce(_Q.done_at, _Q.queued_at).label("at"))
        .join(prospects, prospects.c.id == _Q.prospect_id)
        .order_by(waiting_first, func.coalesce(_Q.done_at, _Q.queued_at).desc(), _Q.id.desc())
        .limit(limit)
    )  # fmt: skip
    return [(int(r.id), str(r.name or ""), r.status, r.reason, r.at) for r in conn.execute(found)]


def cancel(conn: Connection, queue_id: int, now: datetime) -> int | None:
    """Annule une ligne en attente ; rend son prospect, None si rien n'était en attente."""
    waiting = update(mail_queue).where(_Q.id == queue_id, _Q.status == WAITING)
    found = conn.execute(
        waiting.values(status=CANCELLED, done_at=now).returning(_Q.prospect_id)
    ).scalar()
    return int(found) if found is not None else None
