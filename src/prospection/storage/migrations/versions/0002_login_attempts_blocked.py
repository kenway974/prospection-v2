"""0002 : tentatives faites pendant un blocage (journalisées, sans compter)."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.add_column(
        "login_attempts",
        sa.Column("blocked", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_login_attempts_ip_at", "login_attempts", ["ip", "at"])


def downgrade() -> None:
    op.drop_index("ix_login_attempts_ip_at", table_name="login_attempts")
    op.drop_column("login_attempts", "blocked")
