"""0020 : SMS envoyés avec le mail d'audit (C175 à C180) : réglages, file des SMS, SMS
envoyés et numéros qui ont répondu STOP (empreinte du numéro seulement, comme les mails)."""

import sqlalchemy as sa
from alembic import op

TS = sa.DateTime(timezone=True)
STATUSES = "status IN ('attente', 'envoye', 'echec', 'ecarte', 'annule')"


def upgrade() -> None:
    op.create_table(
        "sms_settings",
        sa.Column("id", sa.SmallInteger, primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sender", sa.Text, nullable=False, server_default="Kenny"),
        sa.Column("daily_limit", sa.SmallInteger, nullable=False, server_default="30"),
        sa.Column("optouts_synced_at", TS),
        sa.CheckConstraint("id = 1", name="sms_settings_single_row"),
    )  # fmt: skip
    op.execute("INSERT INTO sms_settings (id) VALUES (1)")
    op.create_table(
        "sms_queue",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("prospect_id", sa.BigInteger,
                  sa.ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("queued_at", TS, nullable=False),
        sa.Column("after_mail", sa.Boolean, nullable=False),  # attend le mail de la file
        sa.Column("due_at", TS),  # sans mail à attendre : quand partir
        sa.Column("kind", sa.Text),  # imposé (relance) ; sinon choisi à l'envoi
        sa.Column("status", sa.Text, nullable=False, server_default="attente"),
        sa.Column("reason", sa.Text), sa.Column("done_at", TS),
        sa.CheckConstraint(STATUSES, name="sms_queue_status"),
    )  # fmt: skip
    op.create_index("sms_queue_one_waiting", "sms_queue", ["prospect_id"], unique=True,
                    postgresql_where=sa.text("status = 'attente'"))  # fmt: skip
    op.create_table(
        "sms_sends",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("prospect_id", sa.BigInteger,
                  sa.ForeignKey("prospects.id", ondelete="SET NULL")),
        sa.Column("phone_hash", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("sent_at", TS, nullable=False),
    )  # fmt: skip
    op.create_table(
        "sms_optouts",
        sa.Column("phone_hash", sa.Text, primary_key=True),
        sa.Column("created_at", TS, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sms_optouts")
    op.drop_table("sms_sends")
    op.drop_index("sms_queue_one_waiting", table_name="sms_queue")
    op.drop_table("sms_queue")
    op.drop_table("sms_settings")


revision = "0020"
down_revision = "0019"
