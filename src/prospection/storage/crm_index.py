"""Fiches déjà au CRM, relues par la tâche de fond (C32) : ID app, SIREN, nom normalisé."""

from sqlalchemy import Column, Connection, Table, Text, delete, select
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.db import metadata

APP_ID, SIREN, NAME = "id", "siren", "nom"
crm_index = Table(
    "crm_index", metadata,
    Column("kind", Text, primary_key=True), Column("value", Text, primary_key=True),
)  # fmt: skip


def replace_index(conn: Connection, entries: set[tuple[str, str]]) -> None:
    conn.execute(delete(crm_index))
    if entries:
        rows = [{"kind": k, "value": v} for k, v in sorted(entries)]
        conn.execute(insert(crm_index).values(rows).on_conflict_do_nothing())


def crm_values(conn: Connection, kind: str) -> frozenset[str]:
    rows = conn.execute(select(crm_index.c.value).where(crm_index.c.kind == kind))
    return frozenset(str(r[0]) for r in rows)
