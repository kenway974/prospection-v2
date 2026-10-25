"""Écran Recherche : estimation, lancement, modèles (C08, C16, C18)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from prospection.application.budget_settings import current_budget
from prospection.application.campaigns import create_campaign
from prospection.domain.campaign_request import CampaignRequest, RawRequest
from prospection.domain.google_cost import Estimate, Pricing, estimate
from prospection.domain.trades import expand_queries, load_trades
from prospection.storage.google_usage import month_usage
from prospection.storage.templates import Template, list_templates, save_template


def estimate_raw(
    engine: Engine, pricing: Pricing, raw: RawRequest, now: datetime, timezone: str
) -> Estimate:
    """Coût au pire de la demande telle que saisie (même incomplète)."""
    queries = expand_queries([t for t in raw.trades if t.strip()], load_trades(), raw.synonyms_on)
    pages = len(queries) * len(raw.zones) * 3
    month = now.astimezone(ZoneInfo(timezone)).strftime("%Y-%m")
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
