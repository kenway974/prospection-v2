"""Ma liste de franchises (C30) et ma liste noire (C33)."""

from collections.abc import Iterable

from sqlalchemy import Connection, delete, insert, select

from prospection.domain.criteria import Exclusions
from prospection.domain.trades import normalize
from prospection.storage.crm_index import APP_ID, NAME, SIREN, crm_values
from prospection.storage.privacy import erased_keys
from prospection.storage.schema_campaigns import exclusion_names

FRANCHISE, BLACKLIST = "franchise", "blacklist"


def _save(conn: Connection, kind: str, names: Iterable[str]) -> None:
    conn.execute(delete(exclusion_names).where(exclusion_names.c.kind == kind))
    rows: dict[str, str] = {}
    for name in names:
        clean = name.strip()[:200]
        if normalize(clean):
            rows.setdefault(normalize(clean), clean)
    if rows:
        values = [{"kind": kind, "name_norm": k, "name": v} for k, v in rows.items()]
        conn.execute(insert(exclusion_names), values)


def save_personal_franchises(conn: Connection, names: Iterable[str]) -> None:
    _save(conn, FRANCHISE, names)


def save_blacklist(conn: Connection, names: Iterable[str]) -> None:
    _save(conn, BLACKLIST, names)


def _names(conn: Connection, kind: str) -> list[tuple[str, str]]:
    e = exclusion_names.c
    rows = conn.execute(select(e.name_norm, e.name).where(e.kind == kind).order_by(e.name))
    return [(r.name_norm, r.name) for r in rows]


def load_exclusions(conn: Connection) -> Exclusions:
    franchises = frozenset(n for n, _ in _names(conn, FRANCHISE))
    blacklist = frozenset(n for n, _ in _names(conn, BLACKLIST))
    return Exclusions(franchises, frozenset(), blacklist, crm_values(conn, APP_ID),
                      crm_values(conn, SIREN), crm_values(conn, NAME),
                      erased_keys(conn))  # fmt: skip


def personal_lists(conn: Connection) -> tuple[list[str], list[str]]:
    return [n for _, n in _names(conn, FRANCHISE)], [n for _, n in _names(conn, BLACKLIST)]
