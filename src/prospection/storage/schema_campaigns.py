"""Tables des campagnes (description pour les requêtes ; créées par la migration 0004)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from prospection.storage.db import metadata

TS = DateTime(timezone=True)

campaigns = Table(
    "campaigns", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False), Column("request_json", JSONB, nullable=False),
    Column("status", Text, nullable=False), Column("stop_reason", Text),
    Column("found", Integer, nullable=False), Column("excluded", Integer, nullable=False),
    Column("qualified", Integer, nullable=False), Column("cost_cents", Integer, nullable=False),
    Column("created_at", TS, nullable=False), Column("updated_at", TS, nullable=False),
    Column("claimed_by", Text), Column("heartbeat_at", TS), Column("retry_at", TS),
    Column("schedule_id", BigInteger),  # campagne lancée par une programmation (C77)
    Column("scheduled", Boolean, nullable=False, server_default="false"),
    Column("refresh_running", Boolean, nullable=False, server_default="false"),  # C76
    Column("kind", Text, nullable=False, server_default="appel"),  # appel ou terrain (C127)
)  # fmt: skip

campaign_steps = Table(
    "campaign_steps", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("campaign_id", BigInteger, ForeignKey("campaigns.id"), nullable=False),
    Column("position", Integer, nullable=False), Column("query", Text, nullable=False),
    Column("keyword", Text, nullable=False), Column("zone_label", Text, nullable=False),
    Column("bias", JSONB), Column("restrict_to_bias", Boolean, nullable=False),
    Column("region", Text), Column("country", Text, nullable=False),
    Column("page_token", Text),
    Column("page_number", Integer, nullable=False), Column("done", Boolean, nullable=False),
    Column("skipped", Boolean, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("kind", Text, nullable=False), Column("registry_json", JSONB),
    Column("pending_page_json", JSONB),  # page payée, gardée jusqu'à son enregistrement (C40)
)  # fmt: skip

prospects = Table(
    "prospects", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("campaign_id", BigInteger, ForeignKey("campaigns.id"), nullable=False),
    Column("place_id", Text, nullable=False), Column("data_json", JSONB, nullable=False),
    Column("keywords", ARRAY(Text), nullable=False), Column("qualified", Boolean, nullable=False),
    Column("reasons", ARRAY(Text), nullable=False), Column("to_check", ARRAY(Text), nullable=False),
    Column("status", Text), Column("created_at", TS, nullable=False),
    Column("contact_name", Text), Column("contact_mobile", Text), Column("contact_email", Text),
    Column("updated_at", TS), Column("company_json", JSONB), Column("registry_status", Text),
    Column("site_json", JSONB),
    Column("refresh_pending", Boolean, nullable=False, server_default="false"),  # C76
    Column("refresh_taken_at", TS),
    Column("speed_checked_at", TS),  # vitesse mobile : dernier essai
    Column("speed_attempts", SmallInteger, nullable=False, server_default="0"),
    UniqueConstraint("campaign_id", "place_id", name="uq_prospect_place"),
)  # fmt: skip

google_usage = Table(
    "google_usage", metadata,
    Column("month", Text, primary_key=True), Column("calls", Integer, nullable=False),
    Column("cost_cents", Integer, nullable=False),
)  # fmt: skip

campaign_events = Table(
    "campaign_events", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("campaign_id", BigInteger, ForeignKey("campaigns.id"), nullable=False),
    Column("at", TS, nullable=False), Column("level", Text, nullable=False),
    Column("message", Text, nullable=False),
)  # fmt: skip

exclusion_names = Table(
    "exclusion_names", metadata,
    Column("kind", Text, primary_key=True), Column("name_norm", Text, primary_key=True),
    Column("name", Text, nullable=False),
)  # fmt: skip

campaign_templates = Table(
    "campaign_templates", metadata,
    Column("name", Text, primary_key=True), Column("request_json", JSONB, nullable=False),
)  # fmt: skip
