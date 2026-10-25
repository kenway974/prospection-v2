"""Formulaire Recherche <-> demande de campagne (traduction seulement, sans règle métier)."""

import re
from dataclasses import dataclass, field

from prospection.domain.campaign_request import (
    CampaignRequest,
    CityZone,
    DepartmentZone,
    RadiusZone,
    RawRequest,
    Zone,
)
from prospection.domain.criteria import Criteria
from prospection.domain.departments import find_department

_COMMUNE = re.compile(r"(\d[0-9AB]\d{3})\|(-?\d{1,3}(?:\.\d+)?)\|(-?\d{1,3}(?:\.\d+)?)\|(.{1,100})")


@dataclass
class ParsedForm:
    raw: RawRequest
    errors: dict[str, str] = field(default_factory=dict)


def _int(value: str, default: int | None) -> int | None:
    value = value.strip()
    return int(value) if value.isdigit() else default


def commune_value(city: CityZone) -> str:
    return f"{city.insee_code}|{city.lat}|{city.lon}|{city.name}"


def _zones(form: dict[str, str], errors: dict[str, str]) -> list[Zone]:
    zones: list[Zone] = []
    commune = form.get("commune", "").strip()
    if commune:
        match = _COMMUNE.fullmatch(commune)
        if not match:
            errors["zones"] = "Choisissez la commune dans la liste."
        else:
            code, lat, lon, name = match.groups()
            city = CityZone(name, code, float(lat), float(lon))
            radius = _int(form.get("rayon", ""), 0) or 0
            zones.append(RadiusZone(city, radius) if radius else city)
    for item in re.split(r"[,;\n]", form.get("departements", "")):
        if item.strip():
            department = find_department(item)
            if department is None:
                errors["zones"] = f"Département inconnu : {item.strip()}."
            else:
                zones.append(department)
    return zones


def parse_form(form: dict[str, str]) -> ParsedForm:
    errors: dict[str, str] = {}
    site = form.get("site", "any")
    phone = form.get("telephone", "with")
    criteria = Criteria(
        min_reviews=_int(form.get("avis_min", ""), None),
        max_reviews=_int(form.get("avis_max", ""), None),
        website=site if site in ("any", "with", "without") else "any",  # type: ignore[arg-type]
        phone=phone if phone in ("any", "with", "mobile") else "with",  # type: ignore[arg-type]
        exclude_franchises=form.get("franchises") == "on",
    )
    raw = RawRequest(
        name=form.get("nom", "")[:100],
        trades=[t[:60] for t in re.split(r"[,;\n]", form.get("metiers", ""))][:10],
        zones=_zones(form, errors),
        target=_int(form.get("nombre", ""), 0) or 0,
        criteria=criteria,
        synonyms_on=form.get("synonymes") == "on",
    )
    return ParsedForm(raw, errors)


def _text(number: int | None) -> str:
    return "" if number is None else str(number)


def request_to_form(request: CampaignRequest) -> dict[str, str]:
    """Pour pré-remplir le formulaire depuis un modèle (C18)."""
    values = {
        "nom": request.name, "metiers": ", ".join(request.trades), "nombre": str(request.target),
        "synonymes": "on" if request.synonyms_on else "",
        "avis_max": _text(request.criteria.max_reviews),
        "avis_min": _text(request.criteria.min_reviews),
        "site": request.criteria.website, "telephone": request.criteria.phone,
        "franchises": "on" if request.criteria.exclude_franchises else "",
        "departements": ", ".join(z.code for z in request.zones if isinstance(z, DepartmentZone)),
        "commune": "", "ville": "", "rayon": "0",
    }  # fmt: skip
    for zone in request.zones:
        if isinstance(zone, (CityZone, RadiusZone)):
            city = zone if isinstance(zone, CityZone) else zone.city
            values.update(commune=commune_value(city), ville=city.label)
            values["rayon"] = str(zone.radius_km) if isinstance(zone, RadiusZone) else "0"
    return values
