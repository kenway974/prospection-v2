"""Tables du suivi dans le temps (description pour les requêtes ; migration 0010)."""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
)

from prospection.storage.db import metadata

TS = DateTime(timezone=True)

alerts = Table(
    "alerts", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("key", Text, nullable=False, unique=True), Column("kind", Text, nullable=False),
    Column("message", Text, nullable=False), Column("link", Text, nullable=False),
    Column("created_at", TS, nullable=False), Column("seen_at", TS),
)  # fmt: skip

campaign_schedules = Table(
    "campaign_schedules", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("template_name", Text, ForeignKey("campaign_templates.name"), nullable=False),
    Column("weekday", SmallInteger, nullable=False), Column("hour", SmallInteger, nullable=False),
    Column("next_run_at", TS, nullable=False), Column("created_at", TS, nullable=False),
    UniqueConstraint("template_name", "weekday", "hour", name="uq_schedule"),
)  # fmt: skip
