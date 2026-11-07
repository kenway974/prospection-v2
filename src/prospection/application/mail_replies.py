"""Réponses au mail d'audit repérées dans la conversation Gmail (C163) : l'en-tête « From »
de chaque message, jamais le contenu. Un message d'un autre expéditeur : réponse, notée sur
la fiche ; un message du serveur de messagerie : refus (C157). Fait par la tâche de fond."""

from contextlib import suppress
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.audit_mail_context import MailBlocked
from prospection.application.mail_bounce import mark_bounced
from prospection.sources.gmail import (
    GmailOAuth,
    GmailRefused,
    GmailRevoked,
    GmailUnavailable,
    access_token,
)
from prospection.sources.gmail_threads import GmailScopeMissing, thread_senders
from prospection.storage.call_tracking import add_note
from prospection.storage.mail_send_log import mark_checked, replies_to_check
from prospection.storage.mail_settings import block_replies, load_gmail, replies_blocked
from prospection.storage.secret_box import SecretBox, UnreadableSecret

BATCH = 20
REPLY_NOTE = "Réponse reçue au mail d'audit : à lire dans Gmail, puis appelez."
_SERVERS = ("mailer-daemon", "postmaster", "mail delivery")


def _token(engine: Engine, box: SecretBox) -> tuple[str, str] | None:
    """(jeton durable, adresse du compte) si Gmail est relié et peut voir les en-têtes."""
    with engine.connect() as conn:
        account, blocked = load_gmail(conn), replies_blocked(conn)
    if account is None or blocked:
        return None
    try:
        return box.decrypt(account.token), account.address.lower()
    except UnreadableSecret:
        return None


def _judge(engine: Engine, box: SecretBox, send_id: int, prospect_id: int, senders: list[str],
           me: str, now: datetime) -> None:  # fmt: skip
    others = [s.lower() for s in senders if me not in s.lower()]
    if any(server in s for s in others for server in _SERVERS):
        with suppress(MailBlocked):  # déjà marqué à la main
            mark_bounced(engine, prospect_id, now, box.pepper)
        with engine.begin() as conn:
            mark_checked(conn, send_id, now, replied=False)
        return
    with engine.begin() as conn:
        mark_checked(conn, send_id, now, replied=bool(others))
        if others:
            add_note(conn, prospect_id, REPLY_NOTE, now)


def check_replies(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    now: datetime,
) -> int:  # fmt: skip
    """Revoit jusqu'à BATCH conversations ; renvoie le nombre revu."""
    account = _token(engine, box) if oauth else None
    with engine.connect() as conn:
        pending = replies_to_check(conn, now, BATCH) if account else []
    if not pending or oauth is None or account is None:
        return 0
    refresh, me = account
    try:
        token = access_token(client, oauth, refresh)
        done = 0
        for send_id, prospect_id, thread_id in pending:
            senders = thread_senders(client, token, thread_id)
            _judge(engine, box, send_id, prospect_id, senders, me, now)
            done += 1
    except GmailScopeMissing:
        with engine.begin() as conn:
            block_replies(conn)  # Réglages → Mail d'audit dira de relier Gmail à nouveau
        return 0
    except (GmailRevoked, GmailUnavailable, GmailRefused):
        return 0
    return done
