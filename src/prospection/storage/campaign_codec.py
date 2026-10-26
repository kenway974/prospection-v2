"""Demande de campagne et établissement <-> JSON (stockage)."""

from dataclasses import asdict
from typing import Any

from prospection.domain.campaign_request import (
    CampaignRequest,
    CityZone,
    DepartmentZone,
    RadiusZone,
    Zone,
)
from prospection.domain.criteria import Criteria
from prospection.domain.place import Circle, Place


def _encode_zone(zone: Zone) -> dict[str, Any]:
    kind = {CityZone: "city", RadiusZone: "radius", DepartmentZone: "department"}[type(zone)]
    return {"kind": kind, **asdict(zone)}


def _decode_zone(data: dict[str, Any]) -> Zone:
    kind = data.pop("kind")
    if kind == "city":
        return CityZone(**data)
    if kind == "radius":
        return RadiusZone(CityZone(**data["city"]), data["radius_km"])
    return DepartmentZone(**data)


def encode_request(request: CampaignRequest) -> dict[str, Any]:
    return {
        "name": request.name,
        "trades": list(request.trades),
        "zones": [_encode_zone(z) for z in request.zones],
        "target": request.target,
        "criteria": asdict(request.criteria),
        "synonyms_on": request.synonyms_on,
        "sources": list(request.sources),
    }


def decode_request(data: dict[str, Any]) -> CampaignRequest:
    return CampaignRequest(
        data["name"],
        tuple(data["trades"]),
        tuple(_decode_zone(dict(z)) for z in data["zones"]),
        data["target"],
        Criteria(**data["criteria"]),
        data["synonyms_on"],
        tuple(data.get("sources", ["google"])),  # campagnes d'avant le lot 4 : Google seul
    )


def encode_place(place: Place) -> dict[str, Any]:
    return asdict(place)


def decode_place(data: dict[str, Any]) -> Place:
    values: dict[str, Any] = dict(data)
    values["types"] = tuple(values["types"])
    values["opening_hours"] = tuple(values["opening_hours"])
    return Place(**values)


def encode_circle(circle: Circle | None) -> dict[str, float] | None:
    return asdict(circle) if circle else None


def decode_circle(data: dict[str, float] | None) -> Circle | None:
    return Circle(**data) if data else None
