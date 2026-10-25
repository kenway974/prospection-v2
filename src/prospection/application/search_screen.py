"""Écran Recherche : estimation, lancement, modèles (C08, C16, C18)."""

from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.budget_settings import current_budget
from prospection.application.campaigns import create_campaign, plan_steps
from prospection.domain.campaign_request import CampaignRequest, CityZone, RawRequest
from prospection.domain.foreign_zones import city_choice_label, find_foreign_cities
from prospection.domain.google_cost import Estimate, Pricing, billing_month, estimate, pages_needed
from prospection.domain.trades import expand_queries, load_trades
from prospection.sources.geo_communes import GeoUnavailable, find_communes
from prospection.storage.google_usage import month_usage
from prospection.storage.templates import (
    Template,
    list_templates,
    save_template,
    template_exists,
)


def estimate_raw(engine: Engine, pricing: Pricing, raw: RawRequest, now: datetime) -> Estimate:
    """Coût au pire de la demande telle que saisie (même incomplète)."""
    keywords = [t.strip() for t in raw.trades if t.strip()]
    pages = pages_needed(len(plan_steps(keywords, raw.zones, raw.synonyms_on)))
    month = billing_month(now)
    with engine.connect() as conn:
        calls, spent = month_usage(conn, month)
    return estimate(pricing, pages, calls, spent, current_budget(engine))


class TemplateNameTaken(ValueError):
    def __init__(self) -> None:
        super().__init__("Un modèle porte déjà ce nom : choisissez-en un autre.")


def launch(engine: Engine, request: CampaignRequest, template: str, now: datetime) -> int:
    """Lève TemplateNameTaken, sans rien lancer, si le nom de modèle est déjà pris (C18)."""
    if template.strip():
        with engine.begin() as conn:
            if template_exists(conn, template):
                raise TemplateNameTaken
            save_template(conn, template, request)
    return create_campaign(engine, request, now)


def templates(engine: Engine) -> list[Template]:
    with engine.connect() as conn:
        return list_templates(conn)


def synonyms(trades_text: str, synonyms_on: bool = True) -> list[str]:
    keywords = [t for t in trades_text.split(",") if t.strip()]
    return expand_queries(keywords, load_trades(), synonyms_on)


@dataclass(frozen=True)
class CitySearch:
    choices: list[CityZone]
    problem: str | None


def choice_label(city: CityZone) -> str:
    """« Saint-Denis (974) » en France, « Liège (Wallonie, Belgique) » ailleurs."""
    return city.label if city.country == "FR" else city_choice_label(city)


def find_city(client: httpx.Client, name: str, country: str = "FR") -> CitySearch:
    """France : service officiel des communes ; ailleurs : fichier de données GeoNames."""
    if country != "FR":
        found = find_foreign_cities(name, country)
        return CitySearch(
            found, None if found else "Aucune ville de ce nom. Vérifiez l'orthographe."
        )
    try:
        found = find_communes(client, name)
    except GeoUnavailable:
        return CitySearch([], "Le service des communes ne répond pas. Réessayez dans un instant.")
    return CitySearch(found, None if found else "Aucune commune de ce nom. Vérifiez l'orthographe.")
