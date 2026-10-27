"""0007 : rapport du site des prospects ; page Google payée gardée avant traitement (C40)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


def upgrade() -> None:
    op.add_column("prospects", sa.Column("site_json", JSONB))
    op.add_column("campaign_steps", sa.Column("pending_page_json", JSONB))


def downgrade() -> None:
    op.drop_column("campaign_steps", "pending_page_json")
    op.drop_column("prospects", "site_json")


revision = "0007"
down_revision = "0006"
