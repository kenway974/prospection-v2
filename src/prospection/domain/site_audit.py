"""Audit rapide d'un site : technologie, problèmes et score sur 100 (C49, C50, C52).

Règles reprises de prospection-bot (services/analyzer.py, version 530ba12), relues : poids
inchangés, année courante passée en paramètre, textes plus courts et concrets.
"""

import re
from dataclasses import dataclass
from functools import cache
from importlib import resources
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel

from prospection.domain.html_page import Page

CRITICAL, MAJOR, MINOR = 15, 10, 5
SLOW_SECONDS = 3.0
MIN_WORDS = 200
_COPYRIGHT = re.compile(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-\u2013]\s*)?(\d{4})", re.IGNORECASE)


class _Signals(BaseModel):
    technologies: dict[str, list[str]]
    tracking: list[str]
    social: list[str]


@cache
def signals() -> _Signals:
    text = resources.files("prospection.data").joinpath("site_signals.yaml").read_text("utf-8")
    return _Signals.model_validate(yaml.safe_load(text))


@dataclass(frozen=True)
class Audit:
    score: int
    problems: tuple[str, ...]
    technology: str | None
    https: bool
    mobile: bool
    contact_form: bool


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


def _social(page: Page) -> bool:
    hosts = [(urlsplit(link).hostname or "").lower() for link in page.links]
    return any(h == s or h.endswith("." + s) for h in hosts for s in signals().social)


def audit(page: Page, url: str, seconds: float, current_year: int) -> Audit:
    """Chaque problème a un poids ; le score part de 100."""
    raw = page.raw.lower()
    words = len(page.text.split())
    updated = _last_update(page, current_year)
    noindex = "noindex" in page.metas.get("robots", "").lower()
    https, mobile = url.lower().startswith("https://"), "viewport" in page.metas
    form = page.forms > 0 or page.email_inputs > 0
    checks = [
        (not https, "Pas de HTTPS", CRITICAL),
        (not mobile, "Pas adapté au mobile", CRITICAL),
        (not form, "Pas de formulaire de contact", CRITICAL),
        (noindex, "Caché de Google (noindex)", CRITICAL),
        (seconds > SLOW_SECONDS, f"Chargement lent ({seconds:.1f} s)".replace(".", ","), MAJOR),
        (not page.title, "Pas de titre de page", MAJOR),
        (not any(t in raw for t in signals().tracking), "Aucun outil de suivi des visites", MAJOR),
        (updated is not None and current_year - updated >= 3,
         f"Site pas mis à jour depuis {updated}", MAJOR),
        (words < MIN_WORDS, f"Très peu de texte ({words} mot{'s' if words > 1 else ''})", MAJOR),
        (not page.metas.get("description", "").strip(), "Pas de description pour Google", MINOR),
        (not page.h1, "Pas de titre principal (H1)", MINOR),
        (not _social(page), "Aucun lien vers les réseaux sociaux", MINOR),
    ]  # fmt: skip
    found = [(text, weight) for failed, text, weight in checks if failed]
    score = max(0, 100 - sum(weight for _, weight in found))
    problems = tuple(text for text, _ in found)
    return Audit(score, problems, technology(page, url), https, mobile, form)
