"""Tout ce qu'il faut savoir avant d'écrire ou d'envoyer le mail d'audit (C145, C146)."""

from dataclasses import dataclass, field
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.mail_material import MailMaterial, mail_material
from prospection.application.prospect_card import UnknownProspect
from prospection.application.prospect_view import emails_of
from prospection.domain.audit_mail import STRUCTURES, Draft, MailPoint, MailSender, draft_mail
from prospection.domain.audit_mail_rules import load_mail_rules
from prospection.domain.email_check import UNCHECKED, VALID, check_email, email_domain
from prospection.domain.mail_message import email_fingerprint
from prospection.domain.mail_settings import sender_of
from prospection.domain.mail_stats import least_used
from prospection.domain.mail_versions import MailVersions
from prospection.sources.gmail import GmailOAuth
from prospection.storage.audit_mails import already_written, opted_out, sent_at
from prospection.storage.mail_domains import mail_servers
from prospection.storage.mail_send_log import version_counts
from prospection.storage.mail_settings import load_gmail, load_mail_settings
from prospection.storage.prospect_list import load_prospect
from prospection.storage.secret_box import SecretBox, UnreadableSecret

SETTINGS = "Réglez d'abord votre nom et votre portfolio dans Réglages → Mail d'audit."
GMAIL = "Reliez votre Gmail dans Réglages → Mail d'audit."
NO_AUDIT = "Ni audit du site ni fiche Google pour ce prospect : rien à dire dans ce mail."
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
    versions: MailVersions | None = None  # versions proposées, les moins utilisées (C162)
    hooks: dict[str, str] = field(default_factory=dict)  # accroches possibles : modèle → texte
    material: MailMaterial | None = None


def _versions(material: MailMaterial, counts: dict[str, dict[str, int]]) -> MailVersions:
    """Les versions les moins utilisées jusqu'ici (C162)."""
    rules = load_mail_rules()
    templates = [template for template, _ in material.hooks]
    hook = least_used(templates, counts.get("hook", {})) if templates else None
    return MailVersions(least_used(rules.objets, counts.get("subject", {})), hook,
                        least_used(STRUCTURES, counts.get("structure", {})))  # fmt: skip


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
        hashes = [email_fingerprint(e, box.pepper) for e in emails]
        blocked_out = opted_out(conn, hashes) | already_written(conn, hashes)
        settings, account, sent_on = (
            load_mail_settings(conn),
            load_gmail(conn),
            sent_at(conn, prospect_id),
        )
        counts = version_counts(conn)
    checks = [check_email(e, servers.get(email_domain(e) or "")) for e in emails]
    recipients = [c.email for c in checks if c.status in (VALID, UNCHECKED)
                  and email_fingerprint(c.email, box.pepper) not in blocked_out]  # fmt: skip
    material = mail_material(engine, box, client, prospect, now)
    points = material.points
    try:
        token = box.decrypt(account.token) if account else None
    except UnreadableSecret:
        token = None
    sender = sender_of(settings)
    problems = [
        (sender is None, SETTINGS), (not (oauth and token), GMAIL), (not base, NO_BASE),
        (not points, NOTHING if material.audited else NO_AUDIT), (not recipients, NO_EMAIL),
    ]  # fmt: skip
    blocked = next((message for failed, message in problems if failed), None)
    return MailContext(
        str(prospect.data.get("name") or ""), material.site, points, recipients, sender,
        account.address if account else None, token, settings.reminder_days, sent_on, blocked,
        _versions(material, counts), dict(material.hooks), material,
    )  # fmt: skip


def draft_for(ctx: MailContext, versions: MailVersions | None) -> Draft | None:
    """Brouillon avec ces versions (C162) ; None s'il n'y a rien à dire ou pas d'expéditeur."""
    v = versions or ctx.versions
    if not ctx.points or ctx.sender is None or v is None:
        return None
    hook = ctx.hooks.get(v.hook) if v.hook else None
    return draft_mail(ctx.points, ctx.company, ctx.site, ctx.sender, hook, v.subject, v.structure)
