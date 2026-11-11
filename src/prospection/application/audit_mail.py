"""Mail d'audit d'un prospect : écran (brouillon, destinataires) et envoi Gmail (C145 à C147).

Un seul envoi par prospect, réservé avant l'appel à Gmail (un double clic n'envoie rien en
double) ; si Gmail refuse, la réservation est retirée. Après l'envoi : note datée et rappel.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import Engine

from prospection.application.audit_mail_context import (
    GMAIL,
    MailBlocked,
    MailContext,
    draft_for,
    load_context,
)
from prospection.application.mail_delivery import (
    DOWN,
    REFUSED,
    REVOKED,
    SETUP,
    UNCERTAIN,
    deliver,
)
from prospection.domain.audit_mail import Draft
from prospection.domain.mail_message import (
    InvalidMail,
    build_message,
    check_draft,
    email_fingerprint,
    unsubscribe_footer,
)
from prospection.domain.mail_versions import MailVersions, SendDetails
from prospection.sources.gmail import (
    GmailOAuth,
    GmailUncertain,
)
from prospection.storage.audit_mails import cancel_send, record_send
from prospection.storage.call_tracking import add_note, plan_action
from prospection.storage.mail_send_log import set_thread
from prospection.storage.secret_box import SecretBox

__all__ = [
    "DOWN", "REFUSED", "REVOKED", "SETUP", "UNCERTAIN", "MailBlocked", "MailScreen",
    "mail_screen", "send_audit_mail",
]  # fmt: skip


@dataclass(frozen=True)
class MailScreen:
    prospect_id: int
    name: str
    blocked: str | None  # ce qui empêche l'envoi, dit avec ce qu'il faut faire
    sent_on: datetime | None
    recipients: list[str]
    draft: Draft | None
    footer: str
    sender: str | None  # adresse Gmail reliée
    versions: MailVersions | None = None  # versions du brouillon proposé (C162)


def mail_screen(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    base: str | None, prospect_id: int, now: datetime,
) -> MailScreen:  # fmt: skip
    ctx = load_context(engine, box, client, oauth, base, prospect_id, now)
    footer = unsubscribe_footer(f"{base or ''}/desinscription/…")
    return MailScreen(prospect_id, ctx.company, ctx.blocked, ctx.sent_on, ctx.recipients,
                      draft_for(ctx, None), footer, ctx.gmail_address, ctx.versions)  # fmt: skip


def send_audit_mail(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    base: str | None, prospect_id: int, to: str, subject: str, body: str, now: datetime,
    timezone: str, versions: MailVersions | None = None,
) -> None:  # fmt: skip
    """MailBlocked (message à afficher) si l'envoi est impossible ; rien n'est alors gardé.
    `versions` : celles du brouillon affiché (C162)."""
    ctx = load_context(engine, box, client, oauth, base, prospect_id, now)
    if ctx.sent_on:
        raise MailBlocked("Mail d'audit déjà envoyé à ce prospect.")
    if ctx.blocked or oauth is None or ctx.sender is None:
        raise MailBlocked(ctx.blocked or GMAIL)
    address = to.strip().lower()
    if address not in ctx.recipients:
        raise MailBlocked("Choisissez une adresse de ce prospect dans la liste.")
    try:
        clean_subject, clean_body = check_draft(subject, body)
    except InvalidMail as error:
        raise MailBlocked(str(error)) from None
    token, details = secrets.token_urlsafe(24), _details(ctx, versions, clean_subject, clean_body)
    with engine.begin() as conn:
        email_print = email_fingerprint(address, box.pepper)
        if not record_send(conn, prospect_id, email_print, token, now, details):
            raise MailBlocked("Mail d'audit déjà envoyé à ce prospect.")
    raw = build_message(ctx.sender.name, ctx.gmail_address or "", address, clean_subject,
                        clean_body, f"{base}/desinscription/{token}")  # fmt: skip
    try:
        thread = deliver(client, ctx.refresh_token or "", oauth, raw)
    except GmailUncertain:  # peut-être parti : gardé envoyé, jamais deux fois
        note = f"Mail d'audit peut-être envoyé à {address} (à vérifier dans Gmail)"
        _after(engine, prospect_id, f"{note} : « {clean_subject} »", ctx.reminder_days, now,
               timezone)  # fmt: skip
        raise MailBlocked(UNCERTAIN) from None
    except MailBlocked:  # refus net : rien n'est parti
        with engine.begin() as conn:
            cancel_send(conn, token)
        raise
    with engine.begin() as conn:
        set_thread(conn, token, thread)
    note = f"Mail d'audit envoyé à {address} : « {clean_subject} »"
    _after(engine, prospect_id, note, ctx.reminder_days, now, timezone)


def _details(ctx: MailContext, versions: MailVersions | None, subject: str, body: str
             ) -> SendDetails | None:  # fmt: skip
    """Ce qu'on garde de l'envoi pour les statistiques (C162)."""
    used = versions or ctx.versions
    draft = draft_for(ctx, used)
    if used is None or draft is None or ctx.material is None:
        return None
    edited = (subject, body) != check_draft(draft.subject, draft.body)
    points = tuple(p.title for p in ctx.points)
    return SendDetails(used, edited, points, ctx.material.profile)


def _after(engine: Engine, prospect_id: int, note: str, days: int, now: datetime, tz: str) -> None:
    """Note datée et rappel pour appeler le prospect (C147)."""
    due = now.astimezone(ZoneInfo(tz)).date() + timedelta(days=days)
    with engine.begin() as conn:
        add_note(conn, prospect_id, note, now)
        plan_action(conn, prospect_id, "rappeler", due, None, now)
