"""Une même entreprise (même fiche Google) déjà contactée par une autre campagne (C182).

Chaque campagne crée ses propres lignes de prospect : sans ce contrôle, une entreprise
retrouvée par un programme recevrait un second mail d'audit, même après un « non » au
téléphone."""

from sqlalchemy import Connection, exists, select

from prospection.domain.call_status import TO_CALL
from prospection.storage.audit_mails import mail_sends
from prospection.storage.mail_queue import WAITING, mail_queue
from prospection.storage.schema_campaigns import prospects


def company_contacted(conn: Connection, prospect_id: int) -> bool:
    """Vrai si une autre ligne de la même fiche a reçu (ou attend) le mail d'audit, ou a
    déjà été appelée."""
    p, other = prospects.c, prospects.alias("other")
    place = select(p.place_id).where(p.id == prospect_id).scalar_subquery()
    mailed = exists().where(mail_sends.c.prospect_id == other.c.id)
    waiting = exists().where(mail_queue.c.prospect_id == other.c.id,
                             mail_queue.c.status == WAITING)  # fmt: skip
    called = other.c.status.is_not(None) & (other.c.status != TO_CALL)
    found = select(other.c.id).where(
        other.c.place_id == place, other.c.id != prospect_id, mailed | waiting | called
    )
    return conn.execute(found.limit(1)).first() is not None
