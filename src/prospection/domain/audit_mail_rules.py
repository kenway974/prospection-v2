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

from prospection.domain.audit_mail_models import Hook, Point, Sector
from prospection.domain.trades import normalize

_WORD = re.compile(r"\w+(?:['\u2019]\w+)*")  # apostrophe droite ou typographique
MAX_HOOK_WORDS = 10  # accroche tirée de l'audit : phrase choc (C171)
RANKS = ("legal", "clients", "suivi", "autre")  # légal, clients perdus, suivi, le reste
VARIABLES = frozenset({"entreprise", "site", "expediteur", "telephone", "portfolio",
                       "calendly", "nombre", "lien", "note", "avis", "ans"})  # fmt: skip


class InvalidMailRules(ValueError):
    """Le fichier des règles du mail est mal formé."""


class MailRules(BaseModel):
    objets: list[str] = Field(min_length=1)
    objets_sans_site: list[str] = Field(min_length=1)
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
    accroches_audit: dict[str, list[str]] = {}  # C171 : code du premier point → phrases choc
    accroche_majuscules: bool = True


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
    texts = [
        *rules.objets, *rules.objets_sans_site, rules.salutation, rules.intro,
        rules.intro_sans_site, rules.portfolio, rules.appel_telephone,
        rules.appel_sans_telephone, rules.calendly, rules.signature, rules.pied_desinscription,
        rules.constat, rules.cout, rules.solution,
    ]  # fmt: skip
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
    for text in [*texts, *_audit_hooks(rules)]:
        _check_text(text)
    return rules


def _audit_hooks(rules: MailRules) -> list[str]:
    """C171 : chaque accroche d'audit parle d'un point connu, en 10 mots au plus."""
    unknown = set(rules.accroches_audit) - set(rules.points)
    if unknown:
        raise InvalidMailRules(f"Accroche liée à un point inconnu : {', '.join(sorted(unknown))}.")
    texts = [t for texts in rules.accroches_audit.values() for t in texts]
    for text in texts:
        if len(_WORD.findall(text)) > MAX_HOOK_WORDS:  # « jusqu'à » : un mot ; « : » : aucun
            raise InvalidMailRules(f"Accroche trop longue (10 mots au plus) : « {text} ».")
    return texts


def hook_templates(rules: MailRules) -> list[str]:
    """Toutes les accroches, dans un ordre stable : celles des faits d'abord (codes de versions
    déjà envoyés inchangés), puis celles de l'audit (C162, C171)."""
    return [*(h.texte for h in rules.accroches), *_audit_hooks(rules)]


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
