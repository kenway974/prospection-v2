"""Fiche d'un prospect, à sa place dans la session d'appel (C103, C109)."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from prospection.application.prospect_view import (
    Insights,
    emails_of,
    insights,
)
from prospection.domain.call_status import proposed_action
from prospection.domain.company_card import registry_lines
from prospection.domain.email_check import email_domain
from prospection.domain.place import web_link
from prospection.domain.site_card import site_lines, site_links
from prospection.storage import prospect_list as store
from prospection.storage.call_tracking import Action, Note, notes, open_action
from prospection.storage.crm_exports import crm_link
from prospection.storage.mail_domains import mail_servers
from prospection.storage.prospect_list import ProspectRow


class UnknownProspect(LookupError):
    """Aucun prospect qualifié avec cet identifiant."""


@dataclass(frozen=True)
class Card:
    prospect: ProspectRow
    tel: str | None
    website: str | None
    maps_url: str | None
    notes: list[Note]
    action: Action | None
    proposal: tuple[str, date] | None  # « Rappeler demain », préparé mais pas enregistré
    company_lines: list[tuple[str, str]]  # bloc « L'entreprise » (registre)
    position: int | None
    total: int
    previous_id: int | None
    next_id: int | None
    site_lines: list[tuple[str, str]] = field(default_factory=list)  # bloc « Le site »
    site_links: list[tuple[str, str]] = field(default_factory=list)
    insights: Insights | None = None  # score, raison, drapeaux, confiance, emails
    crm_url: str | None = None  # fiche créée dans le CRM (C72)


def tel_link(phone: object) -> str | None:
    """Numéro pour un lien `tel:` : chiffres et « + » seulement (texte venu de Google)."""
    digits = re.sub(r"[^\d+]", "", phone) if isinstance(phone, str) else ""
    return digits[:20] or None


def _neighbours(queue: list[int], prospect_id: int) -> tuple[int | None, int | None, int | None]:
    if prospect_id not in queue:
        return None, None, None
    i = queue.index(prospect_id)
    return i + 1, queue[i - 1] if i else None, queue[i + 1] if i + 1 < len(queue) else None


def card(
    engine: Engine, prospect_id: int, now: datetime, timezone: str, in_session: bool = False
) -> Card:
    """Ouverte depuis la session, la fiche y prend sa place et devient le point de reprise."""
    with engine.begin() as conn:
        prospect = store.load_prospect(conn, prospect_id)
        if prospect is None:
            raise UnknownProspect(prospect_id)
        session = store.load_session(conn) if in_session else None
        queue = session.queue if session and prospect_id in session.queue else []
        if queue:
            store.move_session(conn, prospect_id, now)
        found_notes, action = notes(conn, prospect_id), open_action(conn, prospect_id)
        domains = [d for e in emails_of(prospect) if (d := email_domain(e))]
        servers = mail_servers(conn, domains)
        crm_url = web_link(crm_link(conn, prospect_id))
    today = now.astimezone(ZoneInfo(timezone)).date()
    proposal = None if action else proposed_action(prospect.status, today)
    position, previous_id, next_id = _neighbours(queue, prospect_id)
    site = prospect.site
    website = web_link(site.url if site and site.url else prospect.data.get("website"))
    return Card(
        prospect, tel_link(prospect.data.get("phone")), website,
        web_link(prospect.data.get("maps_url")), found_notes, action, proposal,
        registry_lines(prospect.company, prospect.registry_status), position,
        len(queue), previous_id, next_id, site_lines(site), site_links(site),
        insights(prospect, servers, today), crm_url,
    )  # fmt: skip
