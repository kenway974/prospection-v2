"""Étapes « registre » d'une campagne : une par zone (C11, C24, C25, C27)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from prospection.domain.campaign_request import (
    CampaignRequest,
    CityZone,
    RadiusZone,
    Zone,
    department_of,
)
from prospection.domain.registry import REGISTRY
from prospection.domain.trades import naf_prefixes
from prospection.storage.campaign_steps import StepSpec

PARIS = ZoneInfo("Europe/Paris")  # les dates de création du registre sont des dates françaises


def _area(zone: Zone) -> tuple[str, str, str]:
    """Commune (code INSEE) ; un rayon ou un département : tout le département."""
    if isinstance(zone, CityZone):
        return "commune", zone.code, zone.label
    if isinstance(zone, RadiusZone):
        code = department_of(zone.city.code)
        return "departement", code, f"département {code} (le registre ne connaît pas le rayon)"
    return "departement", zone.code, zone.label


def registry_steps(request: CampaignRequest, now: datetime) -> list[StepSpec]:
    """Aucune étape si aucun métier n'a de code d'activité connu (on ne cherche pas au hasard)."""
    nafs = naf_prefixes(request.trades)
    if REGISTRY not in request.sources or not nafs:
        return []
    today = now.astimezone(PARIS).date()
    since = today - timedelta(days=request.criteria.created_within_days - 1)  # aujourd'hui compris
    steps = []
    for zone in request.zones:
        area, code, label = _area(zone)
        query = {"since": since.isoformat(), "until": today.isoformat(), "area": area,
                 "code": code, "naf_prefixes": list(nafs)}  # fmt: skip
        steps.append(StepSpec(
            f"créées récemment · {label}", request.trades[0], zone.label, None,
            kind=REGISTRY, registry=query,
        ))  # fmt: skip
    return steps
