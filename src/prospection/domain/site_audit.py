"""Audit d'un site : technologie, problèmes (avec leur code) et score sur 100 (C49, C50, C52,
C139 à C142).

Règles de base reprises de prospection-bot (services/analyzer.py, version 530ba12) ; RGPD,
sécurité et contact ajoutés le 04/11/2026. Chaque problème garde un code stable : il relie
le problème aux règles du mail d'audit (C145).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from prospection.domain.html_page import Page
from prospection.domain.site_contacts import find_contacts
from prospection.domain.site_findings import (
    CRITICAL,
    LEGACY_GA,
    MINOR,
    Finding,
    ageing_findings,
    basic_findings,
)
from prospection.domain.site_form import (
    BASIC,
    CONTACT_PAGE,
    FOUND,
    NONE,
    UNKNOWN,
    form_detail,
    form_place,
)
from prospection.domain.site_form_quality import best_form, form_findings, missing_questions
from prospection.domain.site_js import BLIND, JS_ONLY, is_js_app
from prospection.domain.site_privacy import privacy_findings
from prospection.domain.site_reach import reach_findings
from prospection.domain.site_signals import signals

__all__ = ["LEGACY_GA", "Audit", "audit", "is_placeholder", "technology"]
BASIC_FORM = "Formulaire basique (nom, email, message)"
ONLY_CONTACT = "Formulaire seulement sur une page Contact : invisible depuis l'accueil"
NO_HTTPS, BROKEN_HTTPS = "Pas de HTTPS", "Pas de HTTPS (ou certificat invalide)"
CLEAR_FORM = " : les messages du formulaire circulent en clair"
# Page d'hébergeur ou de domaine en attente : il n'y a pas de vrai site (titre, H1 ou début).
_PLACEHOLDER = re.compile(
    r"site en (?:cours de )?construction|under construction|nom de domaine est à vendre|"
    r"domain (?:is )?for sale|domaine (?:est )?parqué|parked domain|welcome to nginx|"
    r"apache2? (?:ubuntu |debian )?default page|it works!|page par défaut|default web page",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Audit:
    score: int
    problems: tuple[str, ...]
    technology: str | None
    https: bool
    mobile: bool
    contact_form: bool  # aucun manque constaté (« non vérifié » compte comme présent)
    form_place: str | None = None  # où est le formulaire (C139) ; None : audit ancien
    codes: tuple[str, ...] = ()  # code de chaque problème, dans le même ordre
    form_detail: str | None = None  # basique ou devis détaillé (C153)


def technology(page: Page, url: str) -> str | None:
    generator = page.metas.get("generator", "").lower()
    # Ressources chargées par la page (et son adresse) : un mot ou un lien ne suffit pas
    haystack = " ".join((url, generator, *page.sources)).lower()
    for name, marks in signals().technologies.items():
        if name.lower() in generator or any(m in haystack for m in marks):
            return name
    return None


def is_placeholder(page: Page) -> bool:
    """Page « en construction », par défaut ou de domaine à vendre : aucun vrai site."""
    head = " ".join((page.title, *page.h1, page.text[:300]))
    return bool(_PLACEHOLDER.search(head))


def _basic_text(page: Page, others: Sequence[Page], keywords: Sequence[str]) -> str:
    """« Formulaire basique… », avec les questions utiles au métier qui manquent (C159)."""
    form = best_form([page, *others])
    missing = missing_questions(form, keywords) if form else []
    return BASIC_FORM + (f" : il manque {', '.join(missing)}" if missing else "")


def _security(https: bool, https_failed: bool, has_form: bool) -> list[Finding]:
    """C141 : HTTPS absent, cassé, et ce que cela expose (messages du formulaire)."""
    if https:
        return []
    text = BROKEN_HTTPS if https_failed else NO_HTTPS
    code = "https_broken" if https_failed else "no_https"
    return [(code, text + (CLEAR_FORM if has_form else ""), CRITICAL)]


def audit(
    page: Page, url: str, seconds: float, current_year: int, powered_by: str = "",
    others: Sequence[Page] = (), keywords: Sequence[str] = (), https_failed: bool = False,
    country: str = "FR",
) -> Audit:  # fmt: skip
    """Chaque problème a un poids ; le score part de 100. `powered_by` : en-tête X-Powered-By ;
    `others` : pages Contact lues quand l'accueil n'a pas de formulaire (C138) ; `keywords` :
    métiers recherchés ; `https_failed` : l'adresse https n'a pas répondu, la http oui."""
    https, mobile = url.lower().startswith("https://"), "viewport" in page.metas
    tech = technology(page, url)
    place = form_place(page, others, tech)
    js_app = is_js_app(page)
    if js_app and place not in FOUND:
        place = UNKNOWN  # C152 : le formulaire est peut-être dessiné par JavaScript
    found = _security(https, https_failed, place in FOUND)
    if not mobile:
        found.append(("no_mobile", "Pas adapté au mobile", CRITICAL))
    if place == NONE:
        found.append(("no_form", "Pas de formulaire de contact", CRITICAL))
    found += basic_findings(page, seconds, current_year)
    if place == CONTACT_PAGE:
        found.append(("form_contact_only", ONLY_CONTACT, MINOR))
    detail = form_detail(page, others)
    if detail == BASIC:
        found.append(("form_basic", _basic_text(page, others, keywords), MINOR))
    found += form_findings(page, others, place)
    found += ageing_findings(page, url, powered_by)
    found += privacy_findings(page, collects=place in FOUND)
    found += reach_findings(page, find_contacts(page, country).phones, keywords)
    if js_app:  # C152 : on ne juge pas ce qu'on ne voit pas
        found = [f for f in found if f[0] not in BLIND] + [JS_ONLY]
    score = max(0, 100 - sum(weight for _, _, weight in found))
    problems, codes = tuple(t for _, t, _ in found), tuple(c for c, _, _ in found)
    return Audit(score, problems, tech, https, mobile, place != NONE, place, codes, detail)
