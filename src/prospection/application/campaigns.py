"""Créer, arrêter et suivre une campagne (C10 à C15, C34, C35, C119)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.exc import NoResultFound

from prospection.application.registry_plan import registry_steps
from prospection.domain.campaign_request import CampaignRequest, CityZone, RadiusZone, Zone
from prospection.domain.place import Circle
from prospection.domain.registry import GOOGLE
from prospection.domain.trades import expand_queries, load_trades, normalize
from prospection.storage.campaign_steps import StepSpec, next_step
from prospection.storage.campaigns import (
    Campaign,
    Event,
    add_event,
    load_campaign,
    recent_campaigns,
    recent_events,
    set_status,
)
from prospection.storage.campaigns import create_campaign as store_campaign
from prospection.storage.prospects import exclusion_counts

CITY_BIAS_M = 10_000


@dataclass(frozen=True)
class Progress:
    status: str
    name: str
    found: int
    excluded: int
    qualified: int
    target: int
    cost_cents: int
    stop_reason: str | None
    exclusion_counts: list[tuple[str, int]]
    recent_events: list[Event]
    current_step: str | None = None  # « cuisiniste Lyon · page 2 » tant qu'elle tourne


def _zone_step(query: str, keyword: str, zone: Zone) -> StepSpec:
    if isinstance(zone, CityZone):
        bias = Circle(zone.lat, zone.lon, CITY_BIAS_M)
        return StepSpec(f"{query} {zone.name}", keyword, zone.label, bias, country=zone.country)
    if isinstance(zone, RadiusZone):
        bias = Circle(zone.city.lat, zone.city.lon, zone.radius_km * 1000)
        return StepSpec(
            f"{query} {zone.city.name}", keyword, zone.label, bias, True, country=zone.city.country
        )
    return StepSpec(
        f"{query} {zone.name}", keyword, zone.label, None, region=zone.code, country=zone.country
    )


def plan_steps(keywords: Sequence[str], zones: Sequence[Zone], synonyms_on: bool) -> list[StepSpec]:
    """Une étape par requête (mot-clé ou synonyme) et par zone, sans doublon : un doublon
    serait payé deux fois sans rien trouver de neuf."""
    trades = load_trades()
    steps: list[StepSpec] = []
    seen: set[tuple[str, Zone]] = set()
    for keyword in keywords:
        for query in expand_queries([keyword], trades, synonyms_on):
            for zone in zones:
                if (normalize(query), zone) not in seen:
                    seen.add((normalize(query), zone))
                    steps.append(_zone_step(query, keyword, zone))
    return steps


def build_steps(request: CampaignRequest, now: datetime | None = None) -> list[StepSpec]:
    """Étapes « registre » d'abord (C11), puis les recherches Google Maps."""
    registry = registry_steps(request, now) if now else []
    google = plan_steps(request.trades, request.zones, request.synonyms_on)
    return registry + (google if GOOGLE in request.sources else [])


def create_campaign(engine: Engine, request: CampaignRequest, now: datetime) -> int:
    with engine.begin() as conn:
        campaign_id = store_campaign(conn, request, build_steps(request, now), now)
        add_event(conn, campaign_id, now, "info", "Campagne créée, en attente de démarrage")
    return campaign_id


def request_stop(engine: Engine, campaign_id: int, now: datetime) -> None:
    """Arrêt à la prochaine étape, les trouvés sont gardés (C35) ; rien si elle est finie."""
    with engine.begin() as conn:
        if set_status(conn, campaign_id, "stopping", now, only_from=("queued", "running")):
            add_event(conn, campaign_id, now, "info", "Arrêt demandé")


class UnknownCampaign(LookupError):
    """Aucune campagne avec cet identifiant."""


def latest_campaigns(engine: Engine, limit: int = 5) -> list[Campaign]:
    with engine.connect() as conn:
        return recent_campaigns(conn, limit)


def progress(engine: Engine, campaign_id: int) -> Progress:
    with engine.connect() as conn:
        try:
            c = load_campaign(conn, campaign_id)
        except NoResultFound:
            raise UnknownCampaign(campaign_id) from None
        counts = exclusion_counts(conn, campaign_id)
        events = recent_events(conn, campaign_id, 5)
        step = next_step(conn, campaign_id) if c.status == "running" else None
    current = f"{step.query} · page {step.page_number + 1}" if step else None
    return Progress(
        c.status, c.request.name, c.found, c.excluded, c.qualified, c.request.target,
        c.cost_cents, c.stop_reason, counts, events, current,
    )  # fmt: skip
