"""Prospects qualifiés : recherche, filtre, compteurs, session d'appel (C61, C109, C120)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, Connection, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.schema_calls import call_session
from prospection.storage.schema_campaigns import prospects


@dataclass(frozen=True)
class Session:
    status: str | None
    query: str
    prospect_id: int | None


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _filters(status: str | None, query: str) -> list[ColumnElement[bool]]:
    p = prospects.c
    conditions: list[ColumnElement[bool]] = [p.qualified.is_(True)]
    if status:
        conditions.append(p.status == status)
    if query.strip():
        pattern = _like(query.strip()[:100])
        conditions.append(or_(
            p.data_json["name"].astext.ilike(pattern, escape="\\"),
            p.data_json["address"].astext.ilike(pattern, escape="\\"),
            func.array_to_string(p.keywords, " ").ilike(pattern, escape="\\"),
        ))  # fmt: skip
    return conditions


def prospect_ids(conn: Connection, status: str | None, query: str) -> list[int]:
    """La file d'appel : en attendant le score (lot 6), par date de qualification."""
    p = prospects.c
    rows = conn.execute(select(p.id).where(*_filters(status, query)).order_by(p.created_at, p.id))
    return [int(r.id) for r in rows]


def status_counts(conn: Connection) -> dict[str, int]:
    p = prospects.c
    rows = conn.execute(
        select(p.status, func.count()).where(p.qualified.is_(True)).group_by(p.status)
    )
    return {str(status): int(n) for status, n in rows}


def load_session(conn: Connection) -> Session | None:
    s = call_session.c
    row = conn.execute(select(s.status_filter, s.query, s.prospect_id).where(s.id == 1)).first()
    return Session(row.status_filter, row.query, row.prospect_id) if row else None


def save_session(
    conn: Connection, status: str | None, query: str, prospect_id: int | None, now: datetime
) -> None:
    values = {
        "status_filter": status,
        "query": query,
        "prospect_id": prospect_id,
        "updated_at": now,
    }
    statement = insert(call_session).values(id=1, **values)
    conn.execute(statement.on_conflict_do_update(index_elements=["id"], set_=values))
