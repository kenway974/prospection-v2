"""Mode Terrain : recherche autour de moi, tournée, statut en un geste (C113 à C115).

Une recherche terrain est une campagne ordinaire (même budget, mêmes critères gratuits
d'abord, même tâche de fond), autour d'une position, avec un rayon court.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from prospection.application.call_actions import InvalidInput
from prospection.application.campaigns import UnknownCampaign, create_campaign
from prospection.application.prospect_card import UnknownProspect
from prospection.domain.campaign_request import CityZone, RadiusZone, RawRequest, validate_request
from prospection.domain.criteria import Criteria
from prospection.domain.opening import open_now
from prospection.domain.tour import Stop, order_tour, route_links
from prospection.storage import call_tracking as store
from prospection.storage.campaigns import load_campaign
from prospection.storage.prospect_list import ProspectRow, campaign_rows, load_prospect

CHOICES = {"interesse": "intéressé", "repasser": "à rappeler", "non": "pas intéressé"}


@dataclass(frozen=True)
class FieldSearch:
    lat: float
    lon: float
    label: str
    trades: tuple[str, ...] = ("commerce",)
    radius_km: int = 1
    max_reviews: int | None = 20
    without_site: bool = False
    target: int = 15


@dataclass(frozen=True)
class Tour:
    start: tuple[float, float]
    stops: list[ProspectRow]
    links: list[str] = field(default_factory=list)
    unplaced: list[ProspectRow] = field(default_factory=list)  # position inconnue : hors itinéraire


def start_field(
    engine: Engine, search: FieldSearch, now: datetime, timezone: str = "Europe/Paris"
) -> int:
    """Lève InvalidRequest (champ par champ) si la recherche est incomplète."""
    when = now.astimezone(ZoneInfo(timezone)).strftime("%d/%m %H:%M")
    criteria = Criteria(max_reviews=search.max_reviews, phone="any",
                        website="without" if search.without_site else "any")  # fmt: skip
    zone = RadiusZone(CityZone(search.label[:60] or "Ma position", "", search.lat, search.lon),
                      search.radius_km)  # fmt: skip
    raw = RawRequest(f"Terrain · {search.label[:40]} · {when}", list(search.trades), [zone],
                     search.target, criteria, False)  # fmt: skip
    return create_campaign(engine, validate_request(raw), now)


def field_tour(
    engine: Engine, campaign_id: int, now: datetime, timezone: str, open_only: bool
) -> Tour:
    """Lève UnknownCampaign si la campagne n'est pas une recherche autour d'un point."""
    with engine.connect() as conn:
        zone = load_campaign(conn, campaign_id).request.zones[0]
        rows = [r for r, _ in campaign_rows(conn, campaign_id, qualified=True)]
    if not isinstance(zone, RadiusZone):
        raise UnknownCampaign(campaign_id)
    start = (zone.city.lat, zone.city.lon)
    local = now.astimezone(ZoneInfo(timezone))
    if open_only:  # horaires inconnus : écartés (on ne promet pas une boutique ouverte)
        rows = [r for r in rows if open_now(tuple(r.data.get("opening_hours") or ()), local)]
    placed = [r for r in rows if r.data.get("lat") is not None and r.data.get("lon") is not None]
    by_id = {r.id: r for r in placed}
    ordered = order_tour(start, [Stop(r.id, float(r.data["lat"]), float(r.data["lon"]))
                                 for r in placed])  # fmt: skip
    links = route_links(start, ordered) if ordered else []
    unplaced = [r for r in rows if r.id not in by_id]
    return Tour(start, [by_id[s.id] for s in ordered], links, unplaced)


def mark_stop(engine: Engine, prospect_id: int, choice: str, now: datetime, timezone: str) -> None:
    """Intéressé, repasser (« Passer » demain) ou non, en un geste (C115), d'un seul bloc."""
    status = CHOICES.get(choice)
    if status is None:
        raise InvalidInput("statut", "Choisissez Intéressé, Repasser ou Non.")
    tomorrow = now.astimezone(ZoneInfo(timezone)).date() + timedelta(days=1)
    with engine.begin() as conn:
        if load_prospect(conn, prospect_id) is None:
            raise UnknownProspect(prospect_id)
        store.set_call_status(conn, prospect_id, status, now)
        if choice == "repasser":
            store.plan_action(conn, prospect_id, "passer", tomorrow, None, now)
