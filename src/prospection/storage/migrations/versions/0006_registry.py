"""0006 : registre des entreprises — fiche entreprise des prospects, étapes « registre »."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


def upgrade() -> None:
    op.add_column("prospects", sa.Column("company_json", JSONB))
    op.add_column("prospects", sa.Column("registry_status", sa.Text))  # sûr, à confirmer…
    op.add_column(
        "campaign_steps",
        sa.Column("kind", sa.Text, nullable=False, server_default="google"),
    )
    op.add_column("campaign_steps", sa.Column("registry_json", JSONB))


def downgrade() -> None:
    op.drop_column("campaign_steps", "registry_json")
    op.drop_column("campaign_steps", "kind")
    op.drop_column("prospects", "registry_status")
    op.drop_column("prospects", "company_json")


revision = "0006"
down_revision = "0005"
