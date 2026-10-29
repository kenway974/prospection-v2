"""0013 : vitesse mobile des sites (PageSpeed Insights) : date de la mesure par prospect."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column("prospects", sa.Column("speed_checked_at", sa.DateTime(timezone=True)))
    op.add_column(  # essais : un site qui échoue toujours est abandonné, il ne bloque rien
        "prospects",
        sa.Column("speed_attempts", sa.SmallInteger, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("prospects", "speed_attempts")
    op.drop_column("prospects", "speed_checked_at")


revision = "0013"
down_revision = "0012"
