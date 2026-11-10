"""Ce qu'est devenu le mail d'audit d'un prospect, pour choisir la version du SMS (C177)."""

from dataclasses import dataclass

from sqlalchemy import Connection, select

from prospection.storage.audit_mails import mail_sends
from prospection.storage.mail_queue import mail_queue
from prospection.storage.sms_tables import sms_sends

_S, _Q = mail_sends.c, mail_queue.c


@dataclass(frozen=True)
class MailOutcome:
    queue_status: str | None  # dernière ligne de la file, None sans ligne
    queue_reason: str | None
    sent: bool  # un envoi actif (non refusé)
    bounced: bool  # un envoi refusé par le serveur du destinataire


def mail_outcome(conn: Connection, prospect_id: int) -> MailOutcome:
    last = conn.execute(
        select(_Q.status, _Q.reason).where(_Q.prospect_id == prospect_id)
        .order_by(_Q.id.desc()).limit(1)
    ).first()  # fmt: skip
    sends = conn.execute(select(_S.bounced_at).where(_S.prospect_id == prospect_id)).all()
    return MailOutcome(
        last.status if last else None, last.reason if last else None,
        any(r.bounced_at is None for r in sends), any(r.bounced_at is not None for r in sends),
    )  # fmt: skip


def prospect_sms_kinds(conn: Connection, prospect_id: int) -> set[str]:
    found = select(sms_sends.c.kind).where(sms_sends.c.prospect_id == prospect_id)
    return set(conn.execute(found).scalars())
