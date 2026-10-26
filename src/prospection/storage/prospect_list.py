"""Prospects qualifiés : recherche, tri, compteurs, session d'appel (C61, C109, C120)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Connection, Row, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from prospection.domain.company import Company
from prospection.storage.company_codec import decode_company
from prospection.storage.schema_calls import call_session
from prospection.storage.schema_campaigns import prospects

_P = prospects.c
SORTS = {  # C61 : tri de la liste et de la file d'appel
    "trouves": (_P.created_at, _P.id),
    "nom": (func.lower(_P.data_json["name"].astext), _P.id),
    "ville": (func.lower(_P.data_json["address"].astext), _P.id),
}  # fmt: skip


@dataclass(frozen=True)
class ProspectRow:
    id: int
    data: dict[str, Any]
    keywords: list[str]
    status: str
    to_check: list[str]
    contact: tuple[str | None, str | None, str | None]
    company: Company | None = None


@dataclass(frozen=True)
class Session:
    queue: list[int]
    prospect_id: int | None


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _filters(status: str | None, query: str) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [_P.qualified.is_(True)]
    if status:
        conditions.append(_P.status == status)
    if query.strip():
        pattern = _like(query.strip()[:100])
        conditions.append(or_(
            _P.data_json["name"].astext.ilike(pattern, escape="\\"),
            _P.data_json["address"].astext.ilike(pattern, escape="\\"),
            func.array_to_string(_P.keywords, " ").ilike(pattern, escape="\\"),
        ))  # fmt: skip
    return conditions


_COLUMNS = (
    _P.id, _P.data_json, _P.keywords, _P.status, _P.to_check, _P.contact_name,
    _P.contact_mobile, _P.contact_email, _P.company_json,
)  # fmt: skip


def _row(r: Row[Any, Any, Any, Any, Any, Any, Any, Any, Any]) -> ProspectRow:
    contact = (r.contact_name, r.contact_mobile, r.contact_email)
    company = decode_company(r.company_json) if r.company_json else None
    return ProspectRow(
        r.id, r.data_json, list(r.keywords), r.status, list(r.to_check), contact, company
    )


def prospect_rows(conn: Connection, status: str | None, query: str, sort: str) -> list[ProspectRow]:
    rows = conn.execute(select(*_COLUMNS).where(*_filters(status, query)).order_by(*SORTS[sort]))
    return [_row(r) for r in rows]


def prospect_ids(conn: Connection, status: str | None, query: str, sort: str) -> list[int]:
    rows = conn.execute(select(_P.id).where(*_filters(status, query)).order_by(*SORTS[sort]))
    return [int(r.id) for r in rows]


def load_prospect(conn: Connection, prospect_id: int) -> ProspectRow | None:
    row = conn.execute(
        select(*_COLUMNS).where(_P.id == prospect_id, _P.qualified.is_(True))
    ).first()
    return _row(row) if row else None


def status_counts(conn: Connection, query: str) -> dict[str, int]:
    """Par statut, parmi les prospects qui répondent à la recherche (C120)."""
    rows = conn.execute(
        select(_P.status, func.count()).where(*_filters(None, query)).group_by(_P.status)
    )
    return {str(status): int(n) for status, n in rows}


def load_session(conn: Connection) -> Session | None:
    s = call_session.c
    row = conn.execute(select(s.queue, s.prospect_id).where(s.id == 1)).first()
    return Session([int(i) for i in row.queue], row.prospect_id) if row else None


def start_session(conn: Connection, queue: list[int], now: datetime) -> None:
    """La file est figée : classer un prospect ne le fait pas sortir de la session (C109)."""
    values = {"queue": queue, "prospect_id": queue[0] if queue else None, "updated_at": now}
    statement = insert(call_session).values(id=1, **values)
    conn.execute(statement.on_conflict_do_update(index_elements=["id"], set_=values))


def move_session(conn: Connection, prospect_id: int, now: datetime) -> None:
    conn.execute(
        update(call_session).where(call_session.c.id == 1)
        .values(prospect_id=prospect_id, updated_at=now)
    )  # fmt: skip
