"""Mise en file du mail d'audit de fin de campagne : une seule fois par campagne (C182)."""

from datetime import datetime

from sqlalchemy import Connection, select, update

from prospection.storage.schema_campaigns import campaigns

_C = campaigns.c


def claim_campaign_mails(conn: Connection, campaign_id: int, now: datetime) -> bool:
    """Vrai pour le seul appel qui marque la campagne (dans la même transaction que la mise
    en file : un arrêt entre les deux annule les deux)."""
    done = conn.execute(
        update(campaigns).where(_C.id == campaign_id, _C.mails_queued_at.is_(None))
        .values(mails_queued_at=now).returning(_C.id)
    )  # fmt: skip
    return done.first() is not None


def campaigns_to_mail(conn: Connection, limit: int = 5) -> list[int]:
    """Campagnes finies dont les mails ne sont pas encore en file (arrêt au mauvais moment)."""
    found = select(_C.id).where(_C.status == "done", _C.mails_queued_at.is_(None))
    return list(conn.execute(found.order_by(_C.id).limit(limit)).scalars())
