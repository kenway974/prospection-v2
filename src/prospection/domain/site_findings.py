"""Problèmes de base d'un site : chacun a un code stable, un texte et un poids (C50, C52).

Règles reprises de prospection-bot (services/analyzer.py, version 530ba12), relues : poids
inchangés, année courante passée en paramètre, textes plus courts et concrets. Le code relie
le problème aux règles du mail d'audit (C145) ; le texte peut changer sans casser ce lien.
"""

import re
from urllib.parse import urlsplit

from prospection.domain.html_page import Page
from prospection.domain.site_signals import signals

Finding = tuple[str, str, int]  # code, texte, poids
CRITICAL, MAJOR, MINOR = 15, 10, 5
SLOW_SECONDS = 3.0
MIN_WORDS = 200
_LEGACY_GA = re.compile(r"""['"]UA-\d{4,10}-\d{1,4}['"]""")
_GA4 = re.compile(r"\b(?:G|GTM)-[A-Z0-9]{4,12}\b")
_WORDPRESS = re.compile(r"wordpress\s+(\d+)\.(\d+)", re.IGNORECASE)
_PHP = re.compile(r"php/(\d+)\.(\d+)", re.IGNORECASE)
_COPYRIGHT = re.compile(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-\u2013]\s*)?(\d{4})", re.IGNORECASE)
LEGACY_GA = "Ancien Google Analytics, arrêté en juillet 2023 : plus aucune statistique"
WORDPRESS_CURRENT, PHP_CURRENT, MANY_H1, MANY_UNDESCRIBED = 6, 8, 2, 5


def _last_update(page: Page, current_year: int) -> int | None:
    years = [int(y) for y in _COPYRIGHT.findall(page.raw) if 2000 <= int(y) <= current_year]
    return max(years) if years else None


def _tracking(page: Page, raw: str) -> Finding | None:
    modern = [t for t in signals().tracking if t in raw and t != "google-analytics.com"]
    if _LEGACY_GA.search(page.raw) and not _GA4.search(page.raw) and not (set(modern) - {"gtag("}):
        return ("legacy_ga", LEGACY_GA, MAJOR)
    if not modern and "google-analytics.com" not in raw:
        return ("no_tracking", "Aucun outil de suivi des visites", MAJOR)
    return None


def _social(page: Page) -> bool:
    hosts = [(urlsplit(link).hostname or "").lower() for link in page.links]
    return any(h == s or h.endswith("." + s) for h in hosts for s in signals().social)


def basic_findings(page: Page, seconds: float, current_year: int) -> list[Finding]:
    """Visibilité, vitesse, contenu, fraîcheur (le mobile et le HTTPS sont dans l'audit)."""
    words, updated = len(page.text.split()), _last_update(page, current_year)
    tracking = _tracking(page, page.raw.lower())
    t_code, t_text, t_weight = tracking or ("", "", 0)
    checks = [
        ("noindex" in page.metas.get("robots", "").lower(), "noindex",
         "Caché de Google (noindex)", CRITICAL),
        (seconds > SLOW_SECONDS, "slow",
         f"Chargement lent ({seconds:.1f} s)".replace(".", ","), MAJOR),
        (not page.title, "no_title", "Pas de titre de page", MAJOR),
        (tracking is not None, t_code, t_text, t_weight),
        (updated is not None and current_year - updated >= 3, "outdated",
         f"Site pas mis à jour depuis {updated}", MAJOR),
        (words < MIN_WORDS, "thin_content",
         f"Très peu de texte ({words} mot{'s' if words > 1 else ''})", MAJOR),
        (not page.metas.get("description", "").strip(), "no_description",
         "Pas de description pour Google", MINOR),
        (not page.h1, "no_h1", "Pas de titre principal (H1)", MINOR),
        (not _social(page), "no_social", "Aucun lien vers les réseaux sociaux", MINOR),
    ]  # fmt: skip
    return [(code, text, weight) for failed, code, text, weight in checks if failed]


def ageing_findings(page: Page, url: str, powered_by: str) -> list[Finding]:
    """Signes d'un site vieilli ou mal entretenu (versions, contenu mixte, structure)."""
    found: list[Finding] = []
    wp = _WORDPRESS.search(page.metas.get("generator", ""))
    if wp and int(wp[1]) < WORDPRESS_CURRENT:
        text = f"WordPress ancien (version {wp[1]}.{wp[2]}), plus mis à jour"
        found.append(("old_wordpress", text, MAJOR))
    if (php := _PHP.search(powered_by)) and int(php[1]) < PHP_CURRENT:
        text = f"Serveur PHP ancien ({php[1]}.{php[2]}), sans correctifs de sécurité"
        found.append(("old_php", text, MAJOR))
    insecure = sum(s.lower().startswith("http://") for s in page.sources)
    if url.lower().startswith("https://") and insecure:
        text = f"Fichiers chargés sans sécurité (http) sur une page https ({insecure})"
        found.append(("mixed_content", text, MAJOR))
    if page.h1_count > MANY_H1:
        found.append(("many_h1", f"Plusieurs titres principaux ({page.h1_count} H1)", MINOR))
    if (missing := page.images - len(page.image_alts)) >= MANY_UNDESCRIBED:
        found.append(("missing_alts", f"Images sans description ({missing})", MINOR))
    return found
