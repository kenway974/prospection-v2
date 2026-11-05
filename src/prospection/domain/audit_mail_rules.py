"""Règles du mail d'audit (`data/mail_rules.yaml`), validées au démarrage (C145).

Un texte qui cite une variable inconnue, ou un secteur qui parle d'un point inexistant, est
refusé avec un message qui dit quoi corriger : jamais un mail cassé au moment d'écrire.
"""

from functools import cache
from importlib import resources
from string import Formatter

import yaml
from pydantic import BaseModel, Field, ValidationError

VARIABLES = frozenset({"entreprise", "site", "expediteur", "telephone", "portfolio",
                       "calendly", "nombre", "lien"})  # fmt: skip


class InvalidMailRules(ValueError):
    """Le fichier des règles du mail est mal formé."""


class Point(BaseModel):
    poids: int = Field(ge=0, le=100)
    groupe: str | None = None
    probleme: str
    impact: str
    action: str


class Sector(BaseModel):
    mots: list[str] = Field(min_length=1)
    bonus: dict[str, int] = {}
    impacts: dict[str, str] = {}


class MailRules(BaseModel):
    objet: str
    intro: str
    portfolio: str
    appel_calendly: str
    appel_sans_calendly: str
    signature: str
    signature_telephone: str
    pied_desinscription: str
    points: dict[str, Point]
    secteurs: dict[str, Sector] = {}


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
    texts = [rules.objet, rules.intro, rules.portfolio, rules.appel_calendly,
             rules.appel_sans_calendly, rules.signature, rules.signature_telephone,
             rules.pied_desinscription]  # fmt: skip
    texts += [t for p in rules.points.values() for t in (p.probleme, p.impact, p.action)]
    for name, sector in rules.secteurs.items():
        unknown = (set(sector.bonus) | set(sector.impacts)) - set(rules.points)
        if unknown:
            raise InvalidMailRules(
                f"Le secteur « {name} » parle de points inconnus : {', '.join(sorted(unknown))}."
            )
        texts += list(sector.impacts.values())
    for text in texts:
        _check_text(text)
    return rules


@cache
def load_mail_rules() -> MailRules:
    text = resources.files("prospection.data").joinpath("mail_rules.yaml").read_text("utf-8")
    try:
        return parse_rules(yaml.safe_load(text))
    except yaml.YAMLError as error:
        raise InvalidMailRules(f"Règles du mail illisibles (YAML) : {error}") from None
