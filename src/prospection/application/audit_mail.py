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

from prospection.application.audit_mail_context import GMAIL, MailBlocked, MailContext, load_context
from prospection.domain.audit_mail import Draft, draft_mail
from prospection.domain.mail_message import (
    InvalidMail,
    build_message,
    check_draft,
    email_fingerprint,
    unsubscribe_footer,
)
from prospection.sources.gmail import (
    GmailOAuth,
    GmailRefused,
    GmailRevoked,
    GmailUnavailable,
    GmailUncertain,
    access_token,
    send_raw,
)
from prospection.storage.audit_mails import cancel_send, record_send
from prospection.storage.call_tracking import add_note, plan_action
from prospection.storage.secret_box import SecretBox

__all__ = ["MailBlocked", "MailScreen", "mail_screen", "send_audit_mail"]
REVOKED = "Connexion Gmail expirée : reliez Gmail à nouveau dans Réglages → Mail d'audit."
DOWN = "Gmail ne répond pas : réessayez dans un instant (votre texte est gardé)."
REFUSED = "Gmail a refusé ce mail : vérifiez l'adresse du destinataire."
UNCERTAIN = (
    "Envoi incertain (réponse de Gmail perdue) : regardez dans « Messages envoyés » de Gmail. "
    "Le prospect est marqué « envoyé » pour ne jamais lui écrire deux fois."
)


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


def mail_screen(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    base: str | None, prospect_id: int, now: datetime,
) -> MailScreen:  # fmt: skip
    ctx = load_context(engine, box, client, oauth, base, prospect_id, now)
    draft = (draft_mail(ctx.points, ctx.company, ctx.site, ctx.sender)
             if ctx.points and ctx.sender else None)  # fmt: skip
    footer = unsubscribe_footer(f"{base or ''}/desinscription/…")
    return MailScreen(prospect_id, ctx.company, ctx.blocked, ctx.sent_on, ctx.recipients, draft,
                      footer, ctx.gmail_address)  # fmt: skip


def _deliver(client: httpx.Client, ctx: MailContext, oauth: GmailOAuth, raw: bytes) -> None:
    try:
        send_raw(client, access_token(client, oauth, ctx.refresh_token or ""), raw)
    except GmailRevoked:
        raise MailBlocked(REVOKED) from None
    except GmailUnavailable:
        raise MailBlocked(DOWN) from None
    except GmailRefused:
        raise MailBlocked(REFUSED) from None


def send_audit_mail(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    base: str | None, prospect_id: int, to: str, subject: str, body: str, now: datetime,
    timezone: str,
) -> None:  # fmt: skip
    """MailBlocked (message à afficher) si l'envoi est impossible ; rien n'est alors gardé."""
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
    token = secrets.token_urlsafe(24)
    with engine.begin() as conn:
        if not record_send(conn, prospect_id, email_fingerprint(address, box.pepper), token, now):
            raise MailBlocked("Mail d'audit déjà envoyé à ce prospect.")
    raw = build_message(ctx.sender.name, ctx.gmail_address or "", address, clean_subject,
                        clean_body, f"{base}/desinscription/{token}")  # fmt: skip
    try:
        _deliver(client, ctx, oauth, raw)
    except GmailUncertain:  # peut-être parti : gardé envoyé, jamais deux fois
        note = f"Mail d'audit peut-être envoyé à {address} (à vérifier dans Gmail)"
        _after(engine, prospect_id, f"{note} : « {clean_subject} »", ctx.reminder_days, now,
               timezone)  # fmt: skip
        raise MailBlocked(UNCERTAIN) from None
    except MailBlocked:  # refus net : rien n'est parti
        with engine.begin() as conn:
            cancel_send(conn, token)
        raise
    note = f"Mail d'audit envoyé à {address} : « {clean_subject} »"
    _after(engine, prospect_id, note, ctx.reminder_days, now, timezone)


def _after(engine: Engine, prospect_id: int, note: str, days: int, now: datetime, tz: str) -> None:
    """Note datée et rappel pour appeler le prospect (C147)."""
    due = now.astimezone(ZoneInfo(tz)).date() + timedelta(days=days)
    with engine.begin() as conn:
        add_note(conn, prospect_id, note, now)
        plan_action(conn, prospect_id, "rappeler", due, None, now)
