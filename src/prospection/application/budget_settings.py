"""Budget Google et conditions d'une recherche Google Maps (C07, C08)."""

from dataclasses import dataclass

from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.domain.budget import parse_budget
from prospection.domain.services import Service
from prospection.storage.app_settings import load_app_settings, save_budget
from prospection.storage.secret_box import SecretBox


@dataclass(frozen=True)
class SearchReadiness:
    has_google_key: bool
    budget_cents: int


def current_budget(engine: Engine) -> int:
    """Plafond en centimes ; jamais réglé = 0 € (rester dans le quota gratuit de Google)."""
    with engine.connect() as conn:
        return load_app_settings(conn).google_budget_cents or 0


def set_budget(engine: Engine, text: str) -> None:
    """Lève InvalidBudget si le montant est refusé."""
    cents = parse_budget(text)
    with engine.begin() as conn:
        save_budget(conn, cents)


def search_readiness(engine: Engine, box: SecretBox) -> SearchReadiness:
    """Une clé illisible compte comme absente : elle ne permet aucune recherche."""
    has_key = read_key(engine, box, Service.GOOGLE) is not None
    return SearchReadiness(has_key, current_budget(engine))
