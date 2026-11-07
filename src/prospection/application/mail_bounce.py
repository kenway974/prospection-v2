"""Mail d'audit refusé par le serveur du destinataire (C157).

Le refus est noté avec l'accroche d'appel ; un nouvel envoi devient possible, jamais vers la
même adresse (elle reste dans les envois déjà faits).
"""

from datetime import datetime

from sqlalchemy import Engine

from prospection.application.audit_mail_context import MailBlocked
from prospection.application.prospect_view import emails_of
from prospection.domain.mail_message import email_fingerprint
from prospection.storage.audit_mails import bounce
from prospection.storage.call_tracking import add_note
from prospection.storage.prospect_list import load_prospect

HOOK = (
    "Accroche pour l'appel : « J'ai voulu vous écrire et mon mail a été refusé : votre adresse "
    "ne reçoit pas les mails, vos clients ont sans doute le même problème. »"
)


def mark_bounced(engine: Engine, prospect_id: int, now: datetime, pepper: bytes) -> None:
    """MailBlocked si aucun mail d'audit n'est en cours pour ce prospect."""
    with engine.begin() as conn:
        email_hash = bounce(conn, prospect_id, now)
        if email_hash is None:
            raise MailBlocked("Aucun mail d'audit envoyé à ce prospect : rien à marquer.")
        prospect = load_prospect(conn, prospect_id)
        emails = emails_of(prospect) if prospect else []
        address = next((e for e in emails if email_fingerprint(e, pepper) == email_hash), None)
        who = f"de {address}" if address else "du destinataire"
        add_note(conn, prospect_id, f"Mail d'audit refusé par le serveur {who}. {HOOK}", now)
