"""Connexion à PostgreSQL et description des tables."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Engine,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    SmallInteger,
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

api_keys = Table(
    "api_keys",
    metadata,
    Column("service", Text, primary_key=True),
    Column("ciphertext", LargeBinary, nullable=False),
    Column("saved_at", DateTime(timezone=True), nullable=False),
    Column("tested_at", DateTime(timezone=True)),
    Column("test_ok", Boolean),
    Column("test_message", Text),
)

app_settings = Table(
    "app_settings",
    metadata,
    Column("id", SmallInteger, primary_key=True),
    Column("crm", Text, nullable=False, server_default="none"),
    Column("notion_database_id", Text),
    Column("notion_database_title", Text),
    Column("google_budget_cents", Integer),
    CheckConstraint("id = 1", name="app_settings_single_row"),
)


CONNECT_TIMEOUT_SECONDS = 5


def make_engine(database_url: str) -> Engine:
    """Base qui ne répond pas : abandon au bout de 5 s au lieu de bloquer l'app."""
    url = make_url(database_url).update_query_dict(
        {"connect_timeout": str(CONNECT_TIMEOUT_SECONDS)}
    )
    return create_engine(url, pool_pre_ping=True)
