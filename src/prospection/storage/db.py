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
    make_url,
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


CONNECT_TIMEOUT_SECONDS = 5


def make_engine(database_url: str) -> Engine:
    """Base qui ne répond pas : abandon au bout de 5 s au lieu de bloquer l'app."""
    url = make_url(database_url).update_query_dict(
        {"connect_timeout": str(CONNECT_TIMEOUT_SECONDS)}
    )
    return create_engine(url, pool_pre_ping=True)
