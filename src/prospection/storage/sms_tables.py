"""Tables des SMS (C175 à C180), décrites pour les requêtes (créées par la migration 0020)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    SmallInteger,
    Table,
    Text,
)

from prospection.storage.db import metadata

TS = DateTime(timezone=True)
sms_settings = Table(
    "sms_settings", metadata,
    Column("id", SmallInteger, primary_key=True),
    Column("enabled", Boolean, nullable=False, server_default="false"),
    Column("sender", Text, nullable=False, server_default="Kenny"),
    Column("daily_limit", SmallInteger, nullable=False, server_default="30"),
    Column("optouts_synced_at", TS),
    CheckConstraint("id = 1", name="sms_settings_single_row"),
)  # fmt: skip
sms_queue = Table(
    "sms_queue", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("prospect_id", BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"),
           nullable=False),
    Column("queued_at", TS, nullable=False), Column("after_mail", Boolean, nullable=False),
    Column("due_at", TS), Column("kind", Text),
    Column("status", Text, nullable=False, server_default="attente"),
    Column("reason", Text), Column("done_at", TS),
)  # fmt: skip
sms_sends = Table(
    "sms_sends", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("prospect_id", BigInteger, ForeignKey("prospects.id", ondelete="SET NULL")),
    Column("phone_hash", Text, nullable=False), Column("kind", Text, nullable=False),
    Column("sent_at", TS, nullable=False),
)  # fmt: skip
sms_optouts = Table(
    "sms_optouts", metadata,
    Column("phone_hash", Text, primary_key=True), Column("created_at", TS, nullable=False),
)  # fmt: skip
