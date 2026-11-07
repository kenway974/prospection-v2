"""0018 : statistiques du mail d'audit (C162 à C164) : versions utilisées, texte modifié,
points cités, profil du lead, conversation Gmail et réponse ; détection des réponses à
reconnecter quand Gmail n'en a pas encore le droit."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

TS = sa.DateTime(timezone=True)
COLUMNS = (
    ("subject_version", sa.Text), ("hook_version", sa.Text), ("structure", sa.Text),
    ("edited", sa.Boolean), ("points", ARRAY(sa.Text)), ("profile", JSONB),
    ("thread_id", sa.Text), ("replied_at", TS), ("reply_checked_at", TS),
)  # fmt: skip


def upgrade() -> None:
    for name, kind in COLUMNS:
        op.add_column("mail_sends", sa.Column(name, kind))
    op.add_column("mail_settings", sa.Column("replies_blocked", sa.Boolean, nullable=False,
                                             server_default="false"))  # fmt: skip


def downgrade() -> None:
    op.drop_column("mail_settings", "replies_blocked")
    for name, _ in reversed(COLUMNS):
        op.drop_column("mail_sends", name)


revision = "0018"
down_revision = "0017"
