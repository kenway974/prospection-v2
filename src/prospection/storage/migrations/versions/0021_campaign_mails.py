"""0021 : mise en file du mail d'audit en fin de campagne (C182) faite une seule fois, et
rattrapée après un arrêt. Les campagnes déjà finies sont marquées : rien ne part vers elles."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("mails_queued_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE campaigns SET mails_queued_at = now() WHERE status = 'done'")


def downgrade() -> None:
    op.drop_column("campaigns", "mails_queued_at")


revision = "0021"
down_revision = "0020"
