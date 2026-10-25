"""Créer, arrêter et suivre une campagne (C10 à C15, C34, C35, C119)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.exc import NoResultFound

from prospection.domain.campaign_request import CampaignRequest, CityZone, RadiusZone, Zone
from prospection.domain.place import Circle
from prospection.domain.trades import expand_queries, load_trades
from prospection.storage.campaign_steps import StepSpec
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


def _zone_step(query: str, keyword: str, zone: Zone) -> StepSpec:
    if isinstance(zone, CityZone):
        bias = Circle(zone.lat, zone.lon, CITY_BIAS_M)
        return StepSpec(f"{query} {zone.name}", keyword, zone.label, bias)
    if isinstance(zone, RadiusZone):
        bias = Circle(zone.city.lat, zone.city.lon, zone.radius_km * 1000)
        return StepSpec(f"{query} {zone.city.name}", keyword, zone.label, bias, True)
    return StepSpec(f"{query} {zone.name}", keyword, zone.label, None)


def build_steps(request: CampaignRequest) -> list[StepSpec]:
    """Une étape par requête (mot-clé ou synonyme) et par zone."""
    trades = load_trades()
    steps: list[StepSpec] = []
    for keyword in request.trades:
        for query in expand_queries([keyword], trades, request.synonyms_on):
            steps.extend(_zone_step(query, keyword, zone) for zone in request.zones)
    return steps


def create_campaign(engine: Engine, request: CampaignRequest, now: datetime) -> int:
    with engine.begin() as conn:
        campaign_id = store_campaign(conn, request, build_steps(request), now)
        add_event(conn, campaign_id, now, "info", "Campagne créée, en attente de démarrage")
    return campaign_id


def request_stop(engine: Engine, campaign_id: int, now: datetime) -> None:
    """La campagne s'arrêtera à la prochaine étape ; ce qui est trouvé est gardé (C35)."""
    with engine.begin() as conn:
        if load_campaign(conn, campaign_id).status in {"queued", "running"}:
            set_status(conn, campaign_id, "stopping", now)
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
    return Progress(
        c.status, c.request.name, c.found, c.excluded, c.qualified, c.request.target,
        c.cost_cents, c.stop_reason, counts, events,
    )  # fmt: skip
