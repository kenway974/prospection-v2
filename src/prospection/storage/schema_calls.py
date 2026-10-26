"""Tables du suivi des appels (description pour les requêtes ; créées par la migration 0005)."""

from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, Table, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY

from prospection.storage.db import metadata

TS = DateTime(timezone=True)

prospect_notes = Table(
    "prospect_notes", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("prospect_id", BigInteger, ForeignKey("prospects.id"), nullable=False),
    Column("created_at", TS, nullable=False), Column("text", Text, nullable=False),
)  # fmt: skip

prospect_actions = Table(
    "prospect_actions", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("prospect_id", BigInteger, ForeignKey("prospects.id"), nullable=False),
    Column("kind", Text, nullable=False), Column("due_date", Date, nullable=False),
    Column("due_time", Time), Column("created_at", TS, nullable=False), Column("done_at", TS),
)  # fmt: skip

call_session = Table(
    "call_session", metadata,
    Column("id", Integer, primary_key=True), Column("queue", ARRAY(BigInteger), nullable=False),
    Column("prospect_id", BigInteger),
    Column("updated_at", TS, nullable=False),
)  # fmt: skip
