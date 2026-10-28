"""0010 : alertes dans l'app, campagnes programmées, mise à jour des fiches, rappels
(C76 à C78, C98, C108)."""

import sqlalchemy as sa
from alembic import op

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("key", sa.Text, nullable=False, unique=True),  # une seule alerte par sujet
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("link", sa.Text, nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("seen_at", TS),
    )
    op.create_table(
        "campaign_schedules",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "template_name",
            sa.Text,
            sa.ForeignKey("campaign_templates.name", ondelete="CASCADE", onupdate="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.SmallInteger, nullable=False),
        sa.Column("hour", sa.SmallInteger, nullable=False),
        sa.Column("next_run_at", TS, nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6 AND hour BETWEEN 0 AND 23"),
        sa.UniqueConstraint("template_name", "weekday", "hour", name="uq_schedule"),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "schedule_id",
            sa.BigInteger,
            sa.ForeignKey("campaign_schedules.id", ondelete="SET NULL"),
        ),
    )
    # Lancée par une programmation (reste vrai si la programmation est supprimée) ; mise à
    # jour des fiches en cours (C76).
    for name in ("scheduled", "refresh_running"):
        op.add_column(
            "campaigns", sa.Column(name, sa.Boolean, nullable=False, server_default=sa.false())
        )
    op.add_column(
        "prospects",
        sa.Column("refresh_pending", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column("prospects", sa.Column("refresh_taken_at", TS))  # fiche en cours de lecture
    op.add_column(
        "app_settings",
        sa.Column("reminder_minutes", sa.Integer, nullable=False, server_default="15"),
    )
    op.add_column(
        "app_settings",
        sa.Column("reminder_hour", sa.SmallInteger, nullable=False, server_default="8"),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "reminder_hour")
    op.drop_column("app_settings", "reminder_minutes")
    op.drop_column("prospects", "refresh_taken_at")
    op.drop_column("prospects", "refresh_pending")
    op.drop_column("campaigns", "refresh_running")
    op.drop_column("campaigns", "scheduled")
    op.drop_column("campaigns", "schedule_id")
    op.drop_table("campaign_schedules")
    op.drop_table("alerts")


revision = "0010"
down_revision = "0009"
