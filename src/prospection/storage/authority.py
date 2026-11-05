"""Autorité des domaines (Open PageRank), gardée par domaine (C143)."""

from datetime import datetime

from sqlalchemy import Column, Connection, DateTime, Float, Table, Text, select
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.db import metadata

domain_authority = Table(
    "domain_authority", metadata,
    Column("domain", Text, primary_key=True), Column("rank", Float, nullable=False),
    Column("checked_at", DateTime(timezone=True), nullable=False),
)  # fmt: skip


def load_authority(conn: Connection, domain: str) -> tuple[float, datetime] | None:
    a = domain_authority.c
    row = conn.execute(select(a.rank, a.checked_at).where(a.domain == domain)).first()
    return (float(row.rank), row.checked_at) if row else None


def save_authority(conn: Connection, domain: str, rank: float, now: datetime) -> None:
    statement = insert(domain_authority).values(domain=domain, rank=rank, checked_at=now)
    conn.execute(statement.on_conflict_do_update(
        index_elements=["domain"], set_={"rank": rank, "checked_at": now}))  # fmt: skip
