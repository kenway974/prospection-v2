"""0015 : autorité des domaines (Open PageRank), gardée 30 jours (C143)."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.create_table(
        "domain_authority",
        sa.Column("domain", sa.Text, primary_key=True),
        sa.Column("rank", sa.Float, nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("domain_authority")


revision = "0015"
down_revision = "0014"
