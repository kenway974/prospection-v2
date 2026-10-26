"""Prospects qualifiés : recherche, filtre, compteurs, session d'appel (C61, C109, C120)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Connection, Row, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.schema_calls import call_session
from prospection.storage.schema_campaigns import prospects


@dataclass(frozen=True)
class ProspectRow:
    id: int
    data: dict[str, Any]
    keywords: list[str]
    status: str
    to_check: list[str]
    contact: tuple[str | None, str | None, str | None]


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


def _row(r: Row[Any, Any, Any, Any, Any, Any, Any, Any]) -> ProspectRow:
    contact = (r.contact_name, r.contact_mobile, r.contact_email)
    return ProspectRow(r.id, r.data_json, list(r.keywords), r.status, list(r.to_check), contact)


_COLUMNS = (
    prospects.c.id, prospects.c.data_json, prospects.c.keywords, prospects.c.status,
    prospects.c.to_check, prospects.c.contact_name, prospects.c.contact_mobile,
    prospects.c.contact_email,
)  # fmt: skip


def prospect_rows(conn: Connection, status: str | None, query: str) -> list[ProspectRow]:
    p = prospects.c
    rows = conn.execute(
        select(*_COLUMNS).where(*_filters(status, query)).order_by(p.created_at, p.id)
    )
    return [_row(r) for r in rows]


def load_prospect(conn: Connection, prospect_id: int) -> ProspectRow | None:
    p = prospects.c
    row = conn.execute(select(*_COLUMNS).where(p.id == prospect_id, p.qualified.is_(True))).first()
    return _row(row) if row else None


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
