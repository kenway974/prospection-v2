"""0008 : serveur mail (MX) de chaque domaine d'email, vérifié par la tâche de fond (C53)."""

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.create_table(
        "mail_domains",
        sa.Column("domain", sa.Text, primary_key=True),
        sa.Column("status", sa.Text),  # mx, aucun, inexistant ; vide : DNS muet, à revoir
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mail_domains")


revision = "0008"
down_revision = "0007"
