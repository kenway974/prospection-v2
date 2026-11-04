"""Tout ce qu'il faut savoir avant d'écrire ou d'envoyer le mail d'audit (C145, C146)."""

from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.authority import domain_authority
from prospection.application.prospect_card import UnknownProspect
from prospection.application.prospect_view import emails_of
from prospection.domain.audit_mail import MailPoint, MailSender, choose_points
from prospection.domain.email_check import UNCHECKED, VALID, check_email, email_domain
from prospection.domain.mail_message import email_fingerprint
from prospection.domain.mail_settings import sender_of
from prospection.domain.page_speed import is_slow
from prospection.domain.site_card import LOW_AUTHORITY, site_domain
from prospection.domain.site_report import SiteReport
from prospection.sources.gmail import GmailOAuth
from prospection.storage.audit_mails import already_written, opted_out, sent_at
from prospection.storage.mail_domains import mail_servers
from prospection.storage.mail_settings import load_gmail, load_mail_settings
from prospection.storage.prospect_list import load_prospect
from prospection.storage.secret_box import SecretBox, UnreadableSecret

SETTINGS = "Réglez d'abord votre nom et votre portfolio dans Réglages → Mail d'audit."
GMAIL = "Reliez votre Gmail dans Réglages → Mail d'audit."
NO_AUDIT = "Pas d'audit du site pour ce prospect : rien à dire dans ce mail."
NOTHING = "L'audit n'a relevé aucun point à signaler : pas de mail à envoyer."
NO_EMAIL = "Aucun email utilisable : ajoutez-en un dans « Contact » sur la fiche."
NO_BASE = "Adresse publique de l'app inconnue : ajoutez PUBLIC_URL dans Railway."


class MailBlocked(Exception):
    """L'envoi est impossible ; le message dit quoi faire."""


@dataclass(frozen=True)
class MailContext:
    company: str
    site: str
    points: list[MailPoint]
    recipients: list[str]
    sender: MailSender | None
    gmail_address: str | None
    refresh_token: str | None
    reminder_days: int
    sent_on: datetime | None
    blocked: str | None


def _codes(
    engine: Engine, box: SecretBox, client: httpx.Client, site: SiteReport, now: datetime
) -> list[str]:
    codes = list(site.audit.codes) if site.audit else []
    if site.audit and site.audit.form_place is None:  # audit d'avant C137 : formulaire incertain
        codes = [c for c in codes if c not in ("no_form", "form_contact_only")]
    if site.speed and is_slow(site.speed):
        codes.append("slow_mobile")
    domain = site_domain(site.url)
    rank = domain_authority(engine, box, client, domain, now) if domain else None
    return [*codes, *(["low_authority"] if rank is not None and rank < LOW_AUTHORITY else [])]


def load_context(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    base: str | None, prospect_id: int, now: datetime,
) -> MailContext:  # fmt: skip
    with engine.connect() as conn:
        prospect = load_prospect(conn, prospect_id)
        if prospect is None:
            raise UnknownProspect(prospect_id)
        emails = emails_of(prospect)
        servers = mail_servers(conn, [d for e in emails if (d := email_domain(e))])
        hashes = [email_fingerprint(e) for e in emails]
        blocked_out = opted_out(conn, hashes) | already_written(conn, hashes)
        settings, account, sent_on = (
            load_mail_settings(conn),
            load_gmail(conn),
            sent_at(conn, prospect_id),
        )
    checks = [check_email(e, servers.get(email_domain(e) or "")) for e in emails]
    recipients = [c.email for c in checks if c.status in (VALID, UNCHECKED)
                  and email_fingerprint(c.email) not in blocked_out]  # fmt: skip
    site = prospect.site
    audited = site is not None and site.audit is not None and site.url is not None
    points = (
        choose_points(_codes(engine, box, client, site, now), prospect.keywords)
        if site and audited
        else []
    )
    try:
        token = box.decrypt(account.token) if account else None
    except UnreadableSecret:
        token = None
    sender = sender_of(settings)
    problems = [
        (sender is None, SETTINGS), (not (oauth and token), GMAIL), (not base, NO_BASE),
        (not audited, NO_AUDIT), (audited and not points, NOTHING), (not recipients, NO_EMAIL),
    ]  # fmt: skip
    blocked = next((message for failed, message in problems if failed), None)
    return MailContext(
        str(prospect.data.get("name") or ""), site_domain(site.url if site else None) or "",
        points, recipients, sender, account.address if account else None, token,
        settings.reminder_days, sent_on, blocked,
    )  # fmt: skip
