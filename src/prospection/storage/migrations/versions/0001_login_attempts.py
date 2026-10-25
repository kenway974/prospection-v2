"""0001 : journal des tentatives de connexion."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.Text, nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
    )
    op.create_index("ix_login_attempts_at", "login_attempts", ["at"])


def downgrade() -> None:
    op.drop_index("ix_login_attempts_at", table_name="login_attempts")
    op.drop_table("login_attempts")
