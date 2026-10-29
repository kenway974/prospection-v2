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
    Column("reminder_minutes", Integer, nullable=False, server_default="15"),  # C108
    Column("reminder_hour", SmallInteger, nullable=False, server_default="8"),
    Column("purge_months", SmallInteger, nullable=False, server_default="6"),  # C94
    Column("api_checked_at", DateTime(timezone=True)),  # C99
    Column("api_failures", SmallInteger, nullable=False, server_default="0"),
    Column("quiet_start", SmallInteger, nullable=False, server_default="21"),  # Web Push
    Column("quiet_end", SmallInteger, nullable=False, server_default="8"),
    Column("backup_at", DateTime(timezone=True)),
    Column("backup_error", Text),  # C91
    CheckConstraint("id = 1", name="app_settings_single_row"),
)


CONNECT_TIMEOUT_SECONDS = 5


def make_engine(database_url: str) -> Engine:
    """Base qui ne répond pas : abandon au bout de 5 s au lieu de bloquer l'app."""
    url = make_url(database_url).update_query_dict(
        {"connect_timeout": str(CONNECT_TIMEOUT_SECONDS)}
    )
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)  # valeurs hors journaux
