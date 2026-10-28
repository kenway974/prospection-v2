"""0009 : file d'envoi vers le CRM (C67 à C75) et index des fiches déjà au CRM (C32)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "crm_exports",
        sa.Column(
            "prospect_id",
            sa.BigInteger,
            sa.ForeignKey("prospects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("state", sa.Text, nullable=False),  # en attente, envoyé, échec
        sa.Column("outcome", sa.Text),  # créé, mis à jour
        sa.Column("page_id", sa.Text),
        sa.Column("page_url", sa.Text),
        sa.Column("written_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("error", sa.Text),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("next_try_at", TS, nullable=False),
        sa.Column("batch_at", TS, nullable=False),
        sa.Column("sent_at", TS),
    )
    op.create_table(
        "crm_index",
        sa.Column("kind", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("crm_index")
    op.drop_table("crm_exports")


revision = "0009"
down_revision = "0008"
