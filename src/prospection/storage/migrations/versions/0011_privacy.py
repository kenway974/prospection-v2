"""0011 : durée avant la purge des prospects non retenus (C94), 6 mois par défaut ;
dernière vérification des vraies API (C99) et dernière sauvegarde (C91)."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("purge_months", sa.SmallInteger, nullable=False, server_default="6"),
    )
    op.add_column("app_settings", sa.Column("api_checked_at", sa.DateTime(timezone=True)))
    op.add_column("app_settings", sa.Column("backup_at", sa.DateTime(timezone=True)))
    op.add_column("app_settings", sa.Column("backup_error", sa.Text))


def downgrade() -> None:
    for name in ("backup_error", "backup_at", "api_checked_at"):
        op.drop_column("app_settings", name)
    op.drop_column("app_settings", "purge_months")


revision = "0011"
down_revision = "0010"
