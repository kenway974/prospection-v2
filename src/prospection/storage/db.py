"""Connexion à PostgreSQL et description des tables."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Engine,
    Index,
    MetaData,
    Table,
    Text,
    create_engine,
    false,
)

metadata = MetaData()

login_attempts = Table(
    "login_attempts",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("ip", Text, nullable=False),
    Column("success", Boolean, nullable=False),
    Column("blocked", Boolean, nullable=False, server_default=false()),
    Index("ix_login_attempts_at", "at"),
    Index("ix_login_attempts_ip_at", "ip", "at"),
)


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)
