"""Budget Google et conditions d'une recherche Google Maps (C07, C08)."""

from dataclasses import dataclass

from sqlalchemy import Engine

from prospection.domain.budget import parse_budget
from prospection.domain.services import Service
from prospection.storage.api_keys import load_key
from prospection.storage.app_settings import load_app_settings, save_budget


@dataclass(frozen=True)
class SearchReadiness:
    has_google_key: bool
    budget_cents: int | None


def current_budget(engine: Engine) -> int | None:
    with engine.connect() as conn:
        return load_app_settings(conn).google_budget_cents


def set_budget(engine: Engine, text: str) -> None:
    """Lève InvalidBudget si le montant est refusé."""
    cents = parse_budget(text)
    with engine.begin() as conn:
        save_budget(conn, cents)


def search_readiness(engine: Engine) -> SearchReadiness:
    with engine.connect() as conn:
        has_key = load_key(conn, Service.GOOGLE) is not None
        budget = load_app_settings(conn).google_budget_cents
    return SearchReadiness(has_key, budget)
