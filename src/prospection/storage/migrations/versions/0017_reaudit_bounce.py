"""0017 : nouvel audit demandé depuis la fiche (C156) ; mail d'audit refusé, qui permet un
nouvel envoi vers une autre adresse (C157) : un seul envoi actif (non refusé) par prospect."""

import sqlalchemy as sa
from alembic import op

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.add_column("prospects", sa.Column("reaudit_requested_at", TS))
    op.add_column("mail_sends", sa.Column("bounced_at", TS))
    op.drop_constraint("mail_sends_prospect_id_key", "mail_sends", type_="unique")
    op.create_index("mail_sends_one_active", "mail_sends", ["prospect_id"], unique=True,
                    postgresql_where=sa.text("bounced_at IS NULL"))  # fmt: skip


def downgrade() -> None:
    op.execute("DELETE FROM mail_sends WHERE bounced_at IS NOT NULL")
    op.drop_index("mail_sends_one_active", table_name="mail_sends")
    op.create_unique_constraint("mail_sends_prospect_id_key", "mail_sends", ["prospect_id"])
    op.drop_column("mail_sends", "bounced_at")
    op.drop_column("prospects", "reaudit_requested_at")


revision = "0017"
down_revision = "0016"
