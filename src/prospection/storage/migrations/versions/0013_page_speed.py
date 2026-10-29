"""0013 : vitesse mobile des sites (PageSpeed Insights) : date de la mesure par prospect."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column("prospects", sa.Column("speed_checked_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("prospects", "speed_checked_at")


revision = "0013"
down_revision = "0012"
