"""Adresses auxquelles écrire le mail d'audit d'un prospect, ou pourquoi aucune (C146, C168).

Une adresse doit être valide (ou non vérifiable), jamais désinscrite, jamais déjà écrite
(une adresse ne reçoit qu'un mail d'audit, même pour un autre prospect)."""

from sqlalchemy import Connection

from prospection.application.prospect_view import emails_of
from prospection.domain.email_check import UNCHECKED, VALID, check_email, email_domain
from prospection.domain.mail_message import email_fingerprint
from prospection.storage.audit_mails import already_written, opted_out
from prospection.storage.mail_domains import mail_servers
from prospection.storage.prospect_list import ProspectRow

NO_VALID, OPTED_OUT, WRITTEN = "pas d'email valide", "désinscrit", "adresse déjà écrite"


def usable_recipients(
    conn: Connection, prospect: ProspectRow, pepper: bytes
) -> tuple[list[str], str | None]:
    """Adresses utilisables, la meilleure d'abord ; sinon la raison (dite simplement)."""
    emails = emails_of(prospect)
    servers = mail_servers(conn, [d for e in emails if (d := email_domain(e))])
    checks = [check_email(e, servers.get(email_domain(e) or "")) for e in emails]
    valid = [c.email for c in checks if c.status in (VALID, UNCHECKED)]
    prints = {e: email_fingerprint(e, pepper) for e in valid}
    out, written = (
        opted_out(conn, list(prints.values())),
        already_written(conn, list(prints.values())),
    )
    usable = [e for e in valid if prints[e] not in out | written]
    if usable:
        return usable, None
    if not valid:
        return [], NO_VALID
    return [], OPTED_OUT if any(prints[e] in out for e in valid) else WRITTEN
