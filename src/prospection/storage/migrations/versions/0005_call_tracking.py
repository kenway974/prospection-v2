"""0005 : suivi des appels — contact, notes, prochaine action, session d'appel."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
TS = sa.DateTime(timezone=True)


def _prospect() -> sa.ForeignKey:
    return sa.ForeignKey("prospects.id", ondelete="CASCADE")


def upgrade() -> None:
    for column in ("contact_name", "contact_mobile", "contact_email"):
        op.add_column("prospects", sa.Column(column, sa.Text))
    op.add_column("prospects", sa.Column("updated_at", TS))
    op.create_table(
        "prospect_notes",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("prospect_id", sa.BigInteger, _prospect(), nullable=False, index=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
    )
    op.create_table(
        "prospect_actions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("prospect_id", sa.BigInteger, _prospect(), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("due_time", sa.Time),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("done_at", TS),
    )
    op.create_index(  # une seule action ouverte par prospect
        "uq_open_action", "prospect_actions", ["prospect_id"], unique=True,
        postgresql_where=sa.text("done_at IS NULL"),
    )  # fmt: skip
    op.create_table(
        "call_session",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status_filter", sa.Text),
        sa.Column("query", sa.Text, nullable=False, server_default=""),
        sa.Column("prospect_id", sa.BigInteger, sa.ForeignKey("prospects.id", ondelete="SET NULL")),
        sa.Column("updated_at", TS, nullable=False),
        sa.CheckConstraint("id = 1", name="ck_call_session_single"),
    )


def downgrade() -> None:
    op.drop_table("call_session")
    op.drop_index("uq_open_action", "prospect_actions")
    op.drop_table("prospect_actions")
    op.drop_table("prospect_notes")
    for column in ("updated_at", "contact_email", "contact_mobile", "contact_name"):
        op.drop_column("prospects", column)
