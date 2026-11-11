"""Mail d'audit envoyé automatiquement à la fin d'une campagne (C182).

Les prospects retenus partent en file avec leur SMS, comme un envoi groupé : mêmes
garde-fous (rythme, plafond, heures, écartés avec leur raison). Une seule fois par
campagne : la campagne est marquée dans la même transaction que la mise en file, et une
campagne finie pendant un arrêt est rattrapée. Le journal de la campagne le dit.
"""

from datetime import datetime

from sqlalchemy import Engine

from prospection.application.mail_batch import batch_preview, enqueue_rows
from prospection.application.prospect_selection import MAX_SELECTION
from prospection.storage.campaign_mails import campaigns_to_mail, claim_campaign_mails
from prospection.storage.campaigns import add_event
from prospection.storage.prospects import retained_ids
from prospection.storage.secret_box import SecretBox


def queue_campaign_mails(engine: Engine, box: SecretBox, campaign_id: int, now: datetime) -> int:
    """Rend le nombre de mails mis en file (0 si c'est déjà fait)."""
    with engine.connect() as conn:
        ids = retained_ids(conn, campaign_id)
    chunks = [ids[i : i + MAX_SELECTION] for i in range(0, len(ids), MAX_SELECTION)]
    previews = [batch_preview(engine, box, chunk) for chunk in chunks]
    blocked = next((p.blocked for p in previews if p.blocked), None)
    with engine.begin() as conn:
        if not claim_campaign_mails(conn, campaign_id, now):
            return 0
        if blocked:
            add_event(conn, campaign_id, now, "warning", f"Mail d'audit pas envoyé : {blocked}")
            return 0
        mails: list[int] = []
        texts: list[int] = []
        for preview in previews:
            m, t = enqueue_rows(conn, preview, now, registry_later=True)
            mails, texts = mails + m, texts + t
        skipped = len(ids) - len(set(mails) | set(texts))
        if ids:
            add_event(conn, campaign_id, now, "info",
                      f"Mail d'audit : {len(mails)} en file, {len(texts)} SMS, {skipped} "
                      "écarté(s) (détail : Prospects → Envois du mail d'audit).")  # fmt: skip
    return len(mails)


def catch_up_campaign_mails(engine: Engine, box: SecretBox, now: datetime) -> int:
    """Campagnes finies pendant un arrêt de la tâche de fond : leurs mails partent en file."""
    with engine.connect() as conn:
        pending = campaigns_to_mail(conn)
    for campaign_id in pending:
        queue_campaign_mails(engine, box, campaign_id, now)
    return len(pending)
