"""Fiche « Pour l'appel » : accroche et douleurs probables, par règles fixes (C110, C111).

Les règles vivent dans data/call_rules.yaml (schéma strict : une règle invalide fait échouer
le démarrage et les tests). Les douleurs sont des indices à confirmer, jamais des certitudes.
"""

from dataclasses import dataclass
from functools import cache
from importlib import resources
from string import Formatter

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from prospection.domain.call_sheet_rules import Conditions, matches
from prospection.domain.signals import Signals, months
from prospection.domain.site_guess import address_city

CONFIRM = "Indices à confirmer pendant l'appel, jamais des certitudes."
MAX_PAINS = 3
VARIABLES = {"nom", "métier", "ville", "ancienneté", "note"}


class InvalidRules(ValueError):
    """Le fichier des règles « Pour l'appel » est mal formé."""


def _check_text(text: str) -> str:
    used = {name for _, name, _, _ in Formatter().parse(text) if name is not None}
    if used - VARIABLES:
        raise ValueError(f"variable inconnue : {sorted(used - VARIABLES)}")
    return text


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    priority: int
    when: Conditions
    hook: str | None = None
    pains: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _texts(self) -> "Rule":
        if not self.hook and not self.pains:
            raise ValueError("une règle donne une accroche ou des douleurs")
        for text in (self.hook or "", *self.pains):
            _check_text(text)
        return self


class _File(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: tuple[Rule, ...]


def parse_rules(text: str) -> tuple[Rule, ...]:
    try:
        rules = _File.model_validate(yaml.safe_load(text)).rules
    except (yaml.YAMLError, ValidationError, TypeError) as error:
        raise InvalidRules(f"Règles « Pour l'appel » invalides : {error}") from None
    return tuple(sorted(rules, key=lambda r: -r.priority))


@cache
def load_rules() -> tuple[Rule, ...]:
    return parse_rules(
        resources.files("prospection.data").joinpath("call_rules.yaml").read_text("utf-8")
    )


@dataclass(frozen=True)
class CallSheet:
    hook: str | None
    pains: tuple[str, ...]
    notice: str = CONFIRM


def call_sheet(s: Signals, trade: str, rules: tuple[Rule, ...] | None = None) -> CallSheet:
    rating = f"{s.place.rating:.1f}/5".replace(".", ",") if s.place.rating else ""
    values = {"nom": s.place.name, "métier": trade or "professionnel",
              "ville": address_city(s.place.address) or "votre ville",
              "ancienneté": months(s.age_days) if s.age_days is not None else "",
              "note": rating}  # fmt: skip
    found = [r for r in (rules if rules is not None else load_rules()) if matches(r.when, s)]
    hook = next((r.hook for r in found if r.hook), None)
    pains = list(dict.fromkeys(p for r in found for p in r.pains))[:MAX_PAINS]
    return CallSheet(hook.format_map(values) if hook else None,
                     tuple(p.format_map(values) for p in pains))  # fmt: skip
