"""Étapes « registre » d'une campagne : une par zone (C11, C24, C25, C27)."""

from datetime import date, timedelta

from prospection.domain.campaign_request import CampaignRequest, CityZone, RadiusZone, Zone
from prospection.domain.registry import REGISTRY
from prospection.domain.trades import find_trade, load_trades
from prospection.storage.campaign_steps import StepSpec


def _area(zone: Zone) -> tuple[str, str]:
    """Commune (code INSEE) ; pour un rayon ou un département, le département."""
    if isinstance(zone, CityZone):
        return "commune", zone.code
    code = zone.city.code if isinstance(zone, RadiusZone) else zone.code
    if isinstance(zone, RadiusZone):
        code = code[:3] if code.startswith("97") else code[:2]
    return "departement", code


def naf_prefixes(trades: tuple[str, ...]) -> tuple[str, ...]:
    known = load_trades()
    found = [p for t in trades if (trade := find_trade(t, known)) for p in trade.naf_prefixes]
    return tuple(dict.fromkeys(found))


def registry_steps(request: CampaignRequest, today: date) -> list[StepSpec]:
    """Aucune étape si aucun métier n'a de code d'activité connu (on ne cherche pas au hasard)."""
    nafs = naf_prefixes(request.trades)
    if REGISTRY not in request.sources or not nafs:
        return []
    since = today - timedelta(days=request.criteria.created_within_days)
    steps = []
    for zone in request.zones:
        area, code = _area(zone)
        query = {"since": since.isoformat(), "until": today.isoformat(), "area": area,
                 "code": code, "naf_prefixes": list(nafs)}  # fmt: skip
        steps.append(StepSpec(
            f"créées récemment · {zone.label}", request.trades[0], zone.label, None,
            kind=REGISTRY, registry=query,
        ))  # fmt: skip
    return steps
