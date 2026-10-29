"""0012 : notifications sur le téléphone (Web Push) : téléphones abonnés, alertes envoyées,
heures calmes (21 h à 8 h par défaut)."""

import sqlalchemy as sa
from alembic import op

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("endpoint", sa.Text, nullable=False, unique=True),
        sa.Column("p256dh", sa.Text, nullable=False),
        sa.Column("auth", sa.Text, nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )
    op.add_column("alerts", sa.Column("pushed_at", TS))
    op.add_column(
        "app_settings",
        sa.Column("quiet_start", sa.SmallInteger, nullable=False, server_default="21"),
    )
    op.add_column(
        "app_settings",
        sa.Column("quiet_end", sa.SmallInteger, nullable=False, server_default="8"),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "quiet_end")
    op.drop_column("app_settings", "quiet_start")
    op.drop_column("alerts", "pushed_at")
    op.drop_table("push_subscriptions")


revision = "0012"
down_revision = "0011"
