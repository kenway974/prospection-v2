"""0016 : mail d'audit (C144 à C148) : réglages et compte Gmail (jeton chiffré), envois,
désinscriptions (empreinte de l'adresse seulement, gardée même si le prospect est supprimé)."""

import sqlalchemy as sa
from alembic import op

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "mail_settings",
        sa.Column("id", sa.SmallInteger, primary_key=True),
        sa.Column("sender_name", sa.Text), sa.Column("phone", sa.Text),
        sa.Column("portfolio", sa.Text), sa.Column("calendly", sa.Text),
        sa.Column("reminder_days", sa.SmallInteger, nullable=False, server_default="2"),
        sa.Column("gmail_address", sa.Text), sa.Column("gmail_token", sa.LargeBinary),
        sa.Column("gmail_connected_at", TS),
        sa.CheckConstraint("id = 1", name="mail_settings_single_row"),
    )  # fmt: skip
    op.execute("INSERT INTO mail_settings (id) VALUES (1)")
    op.create_table(
        "mail_sends",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("prospect_id", sa.BigInteger,
                  sa.ForeignKey("prospects.id", ondelete="SET NULL"), unique=True),
        sa.Column("email_hash", sa.Text, nullable=False),
        sa.Column("token", sa.Text, nullable=False, unique=True),
        sa.Column("sent_at", TS, nullable=False),
    )  # fmt: skip
    op.create_table(
        "mail_optouts",
        sa.Column("email_hash", sa.Text, primary_key=True),
        sa.Column("created_at", TS, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mail_optouts")
    op.drop_table("mail_sends")
    op.drop_table("mail_settings")


revision = "0016"
down_revision = "0015"
