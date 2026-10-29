"""0014 : origine des campagnes, recherche sur Internet (« appel ») ou Terrain (C127)."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("kind", sa.Text, nullable=False, server_default="appel"))
    # Avant 0014, une recherche Terrain se reconnaissait à son nom (« Terrain · … »).
    op.execute("UPDATE campaigns SET kind = 'terrain' WHERE name LIKE 'Terrain · %'")


def downgrade() -> None:
    op.drop_column("campaigns", "kind")


revision = "0014"
down_revision = "0013"
