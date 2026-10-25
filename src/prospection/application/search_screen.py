"""Écran Recherche : estimation, lancement, modèles (C08, C16, C18)."""

from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.budget_settings import current_budget
from prospection.application.campaigns import create_campaign, plan_steps
from prospection.domain.campaign_request import CampaignRequest, CityZone, RawRequest
from prospection.domain.google_cost import Estimate, Pricing, billing_month, estimate, pages_needed
from prospection.domain.trades import expand_queries, load_trades
from prospection.sources.geo_communes import GeoUnavailable, find_communes
from prospection.storage.google_usage import month_usage
from prospection.storage.templates import Template, list_templates, save_template


def estimate_raw(engine: Engine, pricing: Pricing, raw: RawRequest, now: datetime) -> Estimate:
    """Coût au pire de la demande telle que saisie (même incomplète)."""
    keywords = [t.strip() for t in raw.trades if t.strip()]
    pages = pages_needed(len(plan_steps(keywords, raw.zones, raw.synonyms_on)))
    month = billing_month(now)
    with engine.connect() as conn:
        calls, spent = month_usage(conn, month)
    return estimate(pricing, pages, calls, spent, current_budget(engine))


def launch(engine: Engine, request: CampaignRequest, template: str, now: datetime) -> int:
    campaign_id = create_campaign(engine, request, now)
    if template.strip():
        with engine.begin() as conn:
            save_template(conn, template, request)
    return campaign_id


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


def find_city(client: httpx.Client, name: str) -> CitySearch:
    try:
        found = find_communes(client, name)
    except GeoUnavailable:
        return CitySearch([], "Le service des communes ne répond pas. Réessayez dans un instant.")
    return CitySearch(found, None if found else "Aucune commune de ce nom. Vérifiez l'orthographe.")
