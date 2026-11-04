"""Adresses d'un prospect encore utilisables : jamais une adresse désinscrite (C148)."""

from collections.abc import Sequence

from sqlalchemy import Connection

from prospection.domain.mail_message import email_fingerprint
from prospection.storage.audit_mails import opted_out


def usable_emails(conn: Connection, pepper: bytes, emails: Sequence[str]) -> list[str]:
    """Les adresses données, sans celles qui ont demandé à ne plus recevoir de mail."""
    prints = {email: email_fingerprint(email, pepper) for email in emails}
    blocked = opted_out(conn, list(prints.values())) if prints else set()
    return [email for email in emails if prints[email] not in blocked]
