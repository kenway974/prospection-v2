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
)

metadata = MetaData()

login_attempts = Table(
    "login_attempts",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("ip", Text, nullable=False),
    Column("success", Boolean, nullable=False),
    Index("ix_login_attempts_at", "at"),
)


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)
