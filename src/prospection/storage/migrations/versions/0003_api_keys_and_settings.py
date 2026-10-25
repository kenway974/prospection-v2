"""0003 : clés API chiffrées et réglages de l'app (ligne unique)."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("service", sa.Text, primary_key=True),
        sa.Column("ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True)),
        sa.Column("test_ok", sa.Boolean),
        sa.Column("test_message", sa.Text),
    )
    op.create_table(
        "app_settings",
        sa.Column("id", sa.SmallInteger, primary_key=True),
        sa.Column("crm", sa.Text, nullable=False, server_default="none"),
        sa.Column("notion_database_id", sa.Text),
        sa.Column("notion_database_title", sa.Text),
        sa.Column("google_budget_cents", sa.Integer),
        sa.CheckConstraint("id = 1", name="app_settings_single_row"),
    )
    op.execute("INSERT INTO app_settings (id) VALUES (1)")


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("api_keys")
