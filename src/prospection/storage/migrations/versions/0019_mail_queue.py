"""0019 : envoi groupé du mail d'audit (C168 à C170) : file d'envoi traitée par la tâche de
fond, plafond par jour et arrêt de la file après des refus de Gmail."""

import sqlalchemy as sa
from alembic import op

TS = sa.DateTime(timezone=True)
STATUSES = "status IN ('attente', 'envoye', 'echec', 'ecarte', 'annule')"


def upgrade() -> None:
    op.create_table(
        "mail_queue",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("prospect_id", sa.BigInteger,
                  sa.ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("queued_at", TS, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="attente"),
        sa.Column("reason", sa.Text),
        sa.Column("done_at", TS),
        sa.Column("gap_seconds", sa.SmallInteger),  # attente avant l'envoi suivant
        sa.CheckConstraint(STATUSES, name="mail_queue_status"),
    )  # fmt: skip
    op.create_index("mail_queue_one_waiting", "mail_queue", ["prospect_id"], unique=True,
                    postgresql_where=sa.text("status = 'attente'"))  # fmt: skip
    op.add_column("mail_settings", sa.Column("daily_limit", sa.SmallInteger, nullable=False,
                                             server_default="30"))  # fmt: skip
    op.add_column("mail_settings", sa.Column("queue_paused", sa.Text))


def downgrade() -> None:
    op.drop_column("mail_settings", "queue_paused")
    op.drop_column("mail_settings", "daily_limit")
    op.drop_index("mail_queue_one_waiting", table_name="mail_queue")
    op.drop_table("mail_queue")


revision = "0019"
down_revision = "0018"
