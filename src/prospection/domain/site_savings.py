"""Simulateur d'aides ou d'économies adapté au métier, quand le site n'en a pas (C165).

Règles et textes dans `simulateurs.yaml`. Une aide n'est citée que si le site en parle : sans
agrément ni label, l'entreprise n'y a peut-être pas droit. Un seul simulateur par audit.
"""

import re
from collections.abc import Sequence
from functools import cache
from importlib import resources

import yaml
from pydantic import BaseModel

from prospection.domain.html_page import Page
from prospection.domain.site_findings import MINOR, Finding
from prospection.domain.trades import normalize

PREFIX = "sim_"


class Simulator(BaseModel):
    code: str
    texte: str
    site: list[str] = []
    metiers: list[str] = []


class SavingsRules(BaseModel):
    deja_present: list[str]
    simulateurs: list[Simulator]


@cache
def savings_rules() -> SavingsRules:
    text = resources.files("prospection.data").joinpath("simulateurs.yaml").read_text("utf-8")
    return SavingsRules.model_validate(yaml.safe_load(text))


def _says(text: str, words: Sequence[str]) -> bool:
    return any(re.search(rf"\b{re.escape(w)}", text) for w in words)


def savings_findings(page: Page, keywords: Sequence[str]) -> list[Finding]:
    """Au plus un simulateur : une aide dont parle le site d'abord, sinon un outil du métier."""
    rules = savings_rules()
    text = normalize(" ".join((page.text, *(label for _, label in page.anchors), *page.links)))
    if _says(text, rules.deja_present):
        return []
    trades = " ".join(normalize(k) for k in keywords)
    chosen = next((s for s in rules.simulateurs if _says(text, s.site)), None) or next(
        (s for s in rules.simulateurs if _says(trades, s.metiers)), None
    )
    return [(PREFIX + chosen.code, chosen.texte, MINOR)] if chosen else []
