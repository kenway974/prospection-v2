"""Règles du mail d'audit (`data/mail_rules.yaml`), validées au démarrage (C145).

Un texte qui cite une variable inconnue, ou un secteur qui parle d'un point inexistant, est
refusé avec un message qui dit quoi corriger : jamais un mail cassé au moment d'écrire.
"""

import re
from collections.abc import Sequence
from functools import cache
from importlib import resources
from string import Formatter

import yaml
from pydantic import BaseModel, Field, ValidationError

from prospection.domain.trades import normalize

VARIABLES = frozenset({"entreprise", "site", "expediteur", "telephone", "portfolio",
                       "calendly", "nombre", "lien", "note", "avis", "ans"})  # fmt: skip


class InvalidMailRules(ValueError):
    """Le fichier des règles du mail est mal formé."""


class Point(BaseModel):
    titre: str = Field(min_length=1, max_length=80)
    poids: int = Field(ge=0, le=100)
    groupe: str | None = None
    probleme: str
    impact: str
    action: str


class Sector(BaseModel):
    mots: list[str] = Field(min_length=1)
    bonus: dict[str, int] = {}
    impacts: dict[str, str] = {}


class Condition(BaseModel):
    """Quand une accroche s'applique (C160) ; un critère absent ne compte pas."""

    note_min: float | None = None
    avis_min: int | None = None
    avec_site: bool | None = None
    age_max_mois: int | None = None
    age_min_ans: int | None = None
    label: str | None = None
    secteur: str | None = None


class Hook(BaseModel):
    quand: Condition
    texte: str


class MailRules(BaseModel):
    objet: str
    salutation: str
    intro: str
    intro_sans_site: str
    constat: str
    cout: str
    solution: str
    portfolio: str
    appel_telephone: str
    appel_sans_telephone: str
    calendly: str
    signature: str
    pied_desinscription: str
    points: dict[str, Point]
    secteurs: dict[str, Sector] = {}
    accroches: list[Hook] = []


def _check_text(text: str) -> None:
    for _, name, spec, conversion in Formatter().parse(text):
        if name is None:
            continue
        if name not in VARIABLES or spec or conversion:
            raise InvalidMailRules(
                f"Variable {{{name}}} inconnue dans les règles du mail : "
                f"utilisez seulement {', '.join(sorted(VARIABLES))}."
            )


def parse_rules(raw: object) -> MailRules:
    try:
        rules = MailRules.model_validate(raw)
    except ValidationError as error:
        raise InvalidMailRules(f"Règles du mail mal formées : {error}") from None
    texts = [rules.objet, rules.salutation, rules.intro, rules.intro_sans_site, rules.portfolio,
             rules.appel_telephone, rules.appel_sans_telephone, rules.calendly, rules.signature,
             rules.pied_desinscription, rules.constat, rules.cout, rules.solution]  # fmt: skip
    texts += [t for p in rules.points.values() for t in (p.titre, p.probleme, p.impact, p.action)]
    for name, sector in rules.secteurs.items():
        unknown = (set(sector.bonus) | set(sector.impacts)) - set(rules.points)
        if unknown:
            raise InvalidMailRules(
                f"Le secteur « {name} » parle de points inconnus : {', '.join(sorted(unknown))}."
            )
        texts += list(sector.impacts.values())
    for hook in rules.accroches:
        if hook.quand.secteur and hook.quand.secteur not in rules.secteurs:
            raise InvalidMailRules(f"Accroche liée à un secteur inconnu : {hook.quand.secteur}.")
        texts.append(hook.texte)
    for text in texts:
        _check_text(text)
    return rules


def sectors_for(rules: MailRules, keywords: Sequence[str]) -> list[str]:
    """Secteurs du mail (santé, accueil…) dont un mot correspond aux métiers recherchés."""
    words = " ".join(normalize(k) for k in keywords)
    return [
        name for name, sector in rules.secteurs.items()
        if any(re.search(rf"\b{re.escape(normalize(w))}", words) for w in sector.mots)
    ]  # fmt: skip


@cache
def load_mail_rules() -> MailRules:
    text = resources.files("prospection.data").joinpath("mail_rules.yaml").read_text("utf-8")
    try:
        return parse_rules(yaml.safe_load(text))
    except yaml.YAMLError as error:
        raise InvalidMailRules(f"Règles du mail illisibles (YAML) : {error}") from None
