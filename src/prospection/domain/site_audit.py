"""Audit rapide d'un site : technologie, problèmes et score sur 100 (C49, C50, C52).

Règles reprises de prospection-bot (services/analyzer.py, version 530ba12), relues : poids
inchangés, année courante passée en paramètre, textes plus courts et concrets.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from prospection.domain.html_page import Page
from prospection.domain.site_form import CONTACT_PAGE, NONE, form_place
from prospection.domain.site_signals import signals

CRITICAL, MAJOR, MINOR = 15, 10, 5
SLOW_SECONDS = 3.0
MIN_WORDS = 200
_LEGACY_GA = re.compile(r"""['"]UA-\d{4,10}-\d{1,4}['"]""")
_GA4 = re.compile(r"\b(?:G|GTM)-[A-Z0-9]{4,12}\b")
_WORDPRESS = re.compile(r"wordpress\s+(\d+)\.(\d+)", re.IGNORECASE)
_PHP = re.compile(r"php/(\d+)\.(\d+)", re.IGNORECASE)
LEGACY_GA = "Ancien Google Analytics, arrêté en juillet 2023 : plus aucune statistique"
ONLY_CONTACT = "Formulaire seulement sur une page Contact : invisible depuis l'accueil"
WORDPRESS_CURRENT, PHP_CURRENT, MANY_H1, MANY_UNDESCRIBED = 6, 8, 2, 5
# Page d'hébergeur ou de domaine en attente : il n'y a pas de vrai site (titre, H1 ou début).
_PLACEHOLDER = re.compile(
    r"site en (?:cours de )?construction|under construction|nom de domaine est à vendre|"
    r"domain (?:is )?for sale|domaine (?:est )?parqué|parked domain|welcome to nginx|"
    r"apache2? (?:ubuntu |debian )?default page|it works!|page par défaut|default web page",
    re.IGNORECASE,
)
_COPYRIGHT = re.compile(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-\u2013]\s*)?(\d{4})", re.IGNORECASE)


@dataclass(frozen=True)
class Audit:
    score: int
    problems: tuple[str, ...]
    technology: str | None
    https: bool
    mobile: bool
    contact_form: bool  # aucun manque constaté (« non vérifié » compte comme présent)
    form_place: str | None = None  # où est le formulaire (C139) ; None : audit ancien


def technology(page: Page, url: str) -> str | None:
    generator = page.metas.get("generator", "").lower()
    # Ressources chargées par la page (et son adresse) : un mot ou un lien ne suffit pas
    haystack = " ".join((url, generator, *page.sources)).lower()
    for name, marks in signals().technologies.items():
        if name.lower() in generator or any(m in haystack for m in marks):
            return name
    return None


def _last_update(page: Page, current_year: int) -> int | None:
    years = [int(y) for y in _COPYRIGHT.findall(page.raw) if 2000 <= int(y) <= current_year]
    return max(years) if years else None


def is_placeholder(page: Page) -> bool:
    """Page « en construction », par défaut ou de domaine à vendre : aucun vrai site."""
    head = " ".join((page.title, *page.h1, page.text[:300]))
    return bool(_PLACEHOLDER.search(head))


def _tracking(page: Page, raw: str) -> str | None:
    """Problème de suivi des visites, ou None."""
    modern = [t for t in signals().tracking if t in raw and t != "google-analytics.com"]
    if _LEGACY_GA.search(page.raw) and not _GA4.search(page.raw) and not (set(modern) - {"gtag("}):
        return LEGACY_GA
    if not modern and "google-analytics.com" not in raw:
        return "Aucun outil de suivi des visites"
    return None


def _ageing(page: Page, url: str, powered_by: str) -> list[tuple[str, int]]:
    """Signes d'un site vieilli ou mal entretenu (versions, contenu mixte, structure)."""
    found = []
    if (wp := _WORDPRESS.search(page.metas.get("generator", ""))) and int(
        wp[1]
    ) < WORDPRESS_CURRENT:
        found.append((f"WordPress ancien (version {wp[1]}.{wp[2]}), plus mis à jour", MAJOR))
    if (php := _PHP.search(powered_by)) and int(php[1]) < PHP_CURRENT:
        found.append(
            (f"Serveur PHP ancien ({php[1]}.{php[2]}), sans correctifs de sécurité", MAJOR)
        )
    insecure = sum(s.lower().startswith("http://") for s in page.sources)
    if url.lower().startswith("https://") and insecure:
        found.append(
            (f"Fichiers chargés sans sécurité (http) sur une page https ({insecure})", MAJOR)
        )
    if page.h1_count > MANY_H1:
        found.append((f"Plusieurs titres principaux ({page.h1_count} H1)", MINOR))
    if (missing := page.images - len(page.image_alts)) >= MANY_UNDESCRIBED:
        found.append((f"Images sans description ({missing})", MINOR))
    return found


def _social(page: Page) -> bool:
    hosts = [(urlsplit(link).hostname or "").lower() for link in page.links]
    return any(h == s or h.endswith("." + s) for h in hosts for s in signals().social)


def audit(
    page: Page, url: str, seconds: float, current_year: int, powered_by: str = "",
    others: Sequence[Page] = (),
) -> Audit:  # fmt: skip
    """Chaque problème a un poids ; le score part de 100. `powered_by` : en-tête X-Powered-By ;
    `others` : pages Contact lues quand l'accueil n'a pas de formulaire (C138)."""
    raw = page.raw.lower()
    words = len(page.text.split())
    updated = _last_update(page, current_year)
    noindex = "noindex" in page.metas.get("robots", "").lower()
    https, mobile = url.lower().startswith("https://"), "viewport" in page.metas
    tech = technology(page, url)
    place = form_place(page, others, tech)
    tracking = _tracking(page, raw)
    checks = [
        (not https, "Pas de HTTPS", CRITICAL),
        (not mobile, "Pas adapté au mobile", CRITICAL),
        (place == NONE, "Pas de formulaire de contact", CRITICAL),
        (noindex, "Caché de Google (noindex)", CRITICAL),
        (seconds > SLOW_SECONDS, f"Chargement lent ({seconds:.1f} s)".replace(".", ","), MAJOR),
        (not page.title, "Pas de titre de page", MAJOR),
        (tracking is not None, tracking or "", MAJOR),
        (updated is not None and current_year - updated >= 3,
         f"Site pas mis à jour depuis {updated}", MAJOR),
        (words < MIN_WORDS, f"Très peu de texte ({words} mot{'s' if words > 1 else ''})", MAJOR),
        (not page.metas.get("description", "").strip(), "Pas de description pour Google", MINOR),
        (not page.h1, "Pas de titre principal (H1)", MINOR),
        (not _social(page), "Aucun lien vers les réseaux sociaux", MINOR),
        (place == CONTACT_PAGE, ONLY_CONTACT, MINOR),
    ]  # fmt: skip
    found = [(text, weight) for failed, text, weight in checks if failed]
    found += _ageing(page, url, powered_by)
    score = max(0, 100 - sum(weight for _, weight in found))
    problems = tuple(text for text, _ in found)
    return Audit(score, problems, tech, https, mobile, place != NONE, place)
