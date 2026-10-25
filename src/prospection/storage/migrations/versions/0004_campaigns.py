"""0004 : campagnes, file des pages, prospects, consommation Google, exclusions, modèles."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0004"
down_revision = "0003"
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("request_json", JSONB, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="queued"),
        sa.Column("stop_reason", sa.Text),
        sa.Column("found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("excluded", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qualified", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        sa.Column("heartbeat_at", TS),
        sa.Column("retry_at", TS),
    )
    op.create_table(
        "campaign_steps",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.BigInteger, sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("keyword", sa.Text, nullable=False),
        sa.Column("zone_label", sa.Text, nullable=False),
        sa.Column("bias", JSONB),
        sa.Column("restrict_to_bias", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("page_token", sa.Text),
        sa.Column("page_number", sa.Integer, nullable=False, server_default="0"),
        sa.Column("done", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
    )  # fmt: skip
    op.create_table(
        "prospects",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.BigInteger, sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("place_id", sa.Text, nullable=False),
        sa.Column("data_json", JSONB, nullable=False),
        sa.Column("keywords", ARRAY(sa.Text), nullable=False),
        sa.Column("qualified", sa.Boolean, nullable=False),
        sa.Column("reasons", ARRAY(sa.Text), nullable=False),
        sa.Column("to_check", ARRAY(sa.Text), nullable=False),
        sa.Column("status", sa.Text),
        sa.Column("created_at", TS, nullable=False),
        sa.UniqueConstraint("campaign_id", "place_id", name="uq_prospect_place"),
    )  # fmt: skip
    op.create_table(
        "google_usage",
        sa.Column("month", sa.Text, primary_key=True),
        sa.Column("calls", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_cents", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "campaign_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.BigInteger, sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("at", TS, nullable=False),
        sa.Column("level", sa.Text, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
    )  # fmt: skip
    op.create_table(
        "exclusion_names",
        sa.Column("kind", sa.Text, primary_key=True),
        sa.Column("name_norm", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
    )
    op.create_table(
        "campaign_templates",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("request_json", JSONB, nullable=False),
    )


def downgrade() -> None:
    for table in [
        "campaign_templates", "exclusion_names", "campaign_events", "google_usage",
        "prospects", "campaign_steps", "campaigns",
    ]:  # fmt: skip
        op.drop_table(table)
