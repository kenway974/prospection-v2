"""Version du SMS selon ce qu'est devenu le mail (C177) : parti, refusé, ou pas de mail."""

from sqlalchemy import Connection

from prospection.application.audit_mail import REFUSED
from prospection.application.mail_recipients import OPTED_OUT
from prospection.storage.mail_outcome import mail_outcome


def sms_version(conn: Connection, prospect_id: int) -> str | None:
    """« mail », « bloque », « sans_mail », ou None : pas de SMS (désinscrit des mails)."""
    o = mail_outcome(conn, prospect_id)
    if o.bounced or (o.queue_status == "echec" and o.queue_reason == REFUSED):
        return "bloque"
    if o.sent:
        return "mail"
    return None if o.queue_reason == OPTED_OUT else "sans_mail"
