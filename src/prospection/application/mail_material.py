"""De quoi écrire le mail d'audit d'un prospect : points (site et fiche Google), domaine du
site, accroche personnalisée (C145, C160, C161)."""

from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.authority import domain_authority
from prospection.application.prospect_view import signals_for
from prospection.domain.audit_mail import MailPoint, choose_points
from prospection.domain.lead_profile import lead_profile
from prospection.domain.mail_hooks import LeadFacts, matching_hooks
from prospection.domain.opportunity import opportunity
from prospection.domain.page_speed import is_slow
from prospection.domain.place_audit import place_findings
from prospection.domain.site_card import LOW_AUTHORITY, site_domain
from prospection.domain.site_report import SiteReport
from prospection.storage.campaign_codec import decode_place
from prospection.storage.prospect_list import ProspectRow
from prospection.storage.secret_box import SecretBox


@dataclass(frozen=True)
class MailMaterial:
    points: list[MailPoint]
    site: str  # domaine du site audité, vide sans site
    hooks: list[tuple[str, str]]  # accroches possibles (modèle, texte), la préférée d'abord
    audited: bool  # le site a été audité
    profile: dict[str, str]  # profil du lead, gardé à l'envoi (C162)


def _site_codes(engine: Engine, box: SecretBox, client: httpx.Client, site: SiteReport,
                now: datetime) -> list[str]:  # fmt: skip
    codes = list(site.audit.codes) if site.audit else []
    if site.audit and site.audit.form_place is None:  # audit d'avant C137 : formulaire incertain
        codes = [c for c in codes if c not in ("no_form", "form_contact_only")]
    if site.speed and is_slow(site.speed):
        codes.append("slow_mobile")
    domain = site_domain(site.url)
    rank = domain_authority(engine, box, client, domain, now) if domain else None
    return [*codes, *(["low_authority"] if rank is not None and rank < LOW_AUTHORITY else [])]


def mail_material(
    engine: Engine, box: SecretBox, client: httpx.Client, prospect: ProspectRow, now: datetime
) -> MailMaterial:
    site = prospect.site
    audited = site is not None and site.audit is not None and site.url is not None
    no_site = site is not None and site.url is None  # analysé : aucun vrai site (C161)
    place = decode_place(prospect.data)
    codes = _site_codes(engine, box, client, site, now) if site and audited else []
    codes += [code for code, _, _ in place_findings(place, no_site)]
    company = prospect.company if prospect.registry_status == "sûr" else None
    facts = LeadFacts(
        place.name, place.rating, place.review_count, company.created if company else None,
        company.labels if company else (), audited, now.date(),
    )  # fmt: skip
    domain = site_domain(site.url) if site and audited else None
    score, _ = opportunity(signals_for(prospect, now.date()))
    form = site.audit.form_detail if site and site.audit else None
    profile = lead_profile(prospect.keywords, place.address, audited, place.rating,
                           place.review_count, score, facts.created, form, now.date())  # fmt: skip
    return MailMaterial(
        choose_points(codes, prospect.keywords), domain or "",
        matching_hooks(facts, prospect.keywords), audited, profile,
    )  # fmt: skip
