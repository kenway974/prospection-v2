"""Mail d'audit envoyé automatiquement à la fin d'une campagne (C182).

Les prospects retenus partent en file avec leur SMS, comme un envoi groupé : mêmes
garde-fous (rythme, plafond, heures, écartés avec leur raison). Le journal de la campagne
dit combien sont partis en file, ou ce qu'il faut régler.
"""

from datetime import datetime

from sqlalchemy import Engine

from prospection.application.mail_batch import batch_preview, enqueue_preview
from prospection.storage.campaigns import add_event
from prospection.storage.prospects import retained_ids
from prospection.storage.secret_box import SecretBox


def queue_campaign_mails(engine: Engine, box: SecretBox, campaign_id: int, now: datetime) -> int:
    """Rend le nombre de mails mis en file."""
    with engine.connect() as conn:
        ids = retained_ids(conn, campaign_id)
    if not ids:
        return 0
    preview = batch_preview(engine, box, ids)
    mails, texts = enqueue_preview(engine, preview, now, registry_later=True)
    skipped = len(preview.rows) - len(set(mails) | set(texts))
    with engine.begin() as conn:
        if preview.blocked:
            add_event(conn, campaign_id, now, "warning",
                      f"Mail d'audit pas envoyé : {preview.blocked}")  # fmt: skip
        else:
            add_event(conn, campaign_id, now, "info",
                      f"Mail d'audit : {len(mails)} en file, {len(texts)} SMS, {skipped} "
                      "écarté(s) (détail : Prospects → Envois du mail d'audit).")  # fmt: skip
    return len(mails)
