"""Coût des appels Google et respect du plafond mensuel (C07, C16, C79).

Les appels sont gratuits jusqu'au quota mensuel de Google ; au-delà, chaque appel
coûte un prix fixe, arrondi au centime supérieur (prudent). Le plafond fixé par le
propriétaire (0 € par défaut) borne ce qui peut être dépensé au-delà du gratuit.
"""

import math
from dataclasses import dataclass
from decimal import Decimal
from importlib import resources
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_PAGES_PER_QUERY = 3


class InvalidPricingFile(ValueError):
    """Le fichier des tarifs Google est mal formé."""


class Pricing(BaseModel):
    model_config = ConfigDict(frozen=True)
    free_per_month: int = Field(ge=0)
    usd_per_1000: Decimal = Field(gt=0)
    eur_per_usd: Decimal = Field(gt=0)


@dataclass(frozen=True)
class Estimate:
    pages: int
    free_pages: int
    paid_cents: int
    fits: bool


def load_pricing(path: Path | None = None) -> Pricing:
    if path is None:
        source = resources.files("prospection.data").joinpath("google_pricing.yaml")
        text = source.read_text("utf-8")
    else:
        text = path.read_text("utf-8")
    try:
        return Pricing.model_validate(yaml.safe_load(text))
    except (yaml.YAMLError, ValidationError) as error:
        raise InvalidPricingFile(f"Fichier des tarifs Google invalide : {error}") from None


def _paid_call_cents(pricing: Pricing) -> int:
    cents = pricing.usd_per_1000 * pricing.eur_per_usd * 100 / 1000
    return math.ceil(cents)


def call_cost_cents(pricing: Pricing, calls_this_month: int) -> int:
    """Coût du prochain appel, sachant combien ont déjà été faits ce mois-ci."""
    if calls_this_month < pricing.free_per_month:
        return 0
    return _paid_call_cents(pricing)


def can_call(pricing: Pricing, calls_this_month: int, spent_cents: int, budget_cents: int) -> bool:
    """Vrai si le prochain appel reste dans le gratuit, ou dans le plafond restant."""
    return spent_cents + call_cost_cents(pricing, calls_this_month) <= budget_cents


def estimate(
    pricing: Pricing, pages: int, calls_this_month: int, spent_cents: int, budget_cents: int
) -> Estimate:
    """Coût au pire si toutes les pages sont lues (la campagne s'arrête souvent avant)."""
    free_left = max(0, pricing.free_per_month - calls_this_month)
    free_pages = min(pages, free_left)
    paid_cents = (pages - free_pages) * _paid_call_cents(pricing)
    return Estimate(pages, free_pages, paid_cents, spent_cents + paid_cents <= budget_cents)


def pages_needed(steps: int, max_pages: int = MAX_PAGES_PER_QUERY) -> int:
    """Au pire : chaque étape (requête et zone) lit toutes ses pages."""
    return steps * max_pages
