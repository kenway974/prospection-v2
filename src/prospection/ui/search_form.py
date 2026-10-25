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
from prospection.domain.foreign_zones import (
    countries,
    find_region,
    resolve_foreign_city,
    unknown_region_message,
)
from prospection.domain.place import clip

_COORD = r"(-?\d{1,3}(?:\.\d+)?)"
_COMMUNE = re.compile(rf"([A-Z]{{2}})\|([0-9A-Z]{{0,5}})\|{_COORD}\|{_COORD}\|(.{{1,100}})")


_INSEE = re.compile(r"\d[0-9AB]\d{3}")
MAX_DEPARTMENTS = 20
MAX_FIELD = 500


@dataclass
class ParsedForm:
    raw: RawRequest
    errors: dict[str, str] = field(default_factory=dict)


def _int(value: str, default: int | None) -> int | None:
    value = value.strip()
    return int(value) if value.isascii() and value.isdigit() and len(value) < 7 else default


def commune_value(city: CityZone) -> str:
    return f"{city.country}|{city.code}|{city.lat}|{city.lon}|{city.name}"


def _region(item: str, country: str) -> DepartmentZone | None:
    return find_department(item) if country == "FR" else find_region(item, country)


def _city(commune: str, country: str, errors: dict[str, str]) -> CityZone | None:
    """Hors de France, la ville est retrouvée dans les données ; en France, le code INSEE
    est exigé. Une valeur trafiquée est refusée."""
    match = _COMMUNE.fullmatch(commune)
    if match and match.group(1) != country:
        errors["zones"] = "Cette ville n'est pas dans le pays choisi : cherchez-la à nouveau."
        return None
    city = None
    if match and country != "FR":
        city = resolve_foreign_city(match.group(5), match.group(2), country)
    elif match and _INSEE.fullmatch(match.group(2)):
        _, code, lat, lon, name = match.groups()
        city = CityZone(clip(name, 100) or "", code, float(lat), float(lon))
    if city is None:
        errors["zones"] = "Choisissez la commune dans la liste."
    return city


def _zones(form: dict[str, str], errors: dict[str, str]) -> list[Zone]:
    zones: list[Zone] = []
    country = form.get("pays", "FR")
    if country not in countries():
        errors["zones"] = "Choisissez un pays de la liste."
        return zones
    commune = form.get("commune", "").strip()
    if commune:
        city = _city(commune, country, errors)
        if city is not None:
            radius = _int(form.get("rayon", ""), 0) or 0
            zones.append(RadiusZone(city, radius) if radius else city)
    items = [i for i in re.split(r"[,;\n]", form.get("departements", "")) if i.strip()]
    if len(items) > MAX_DEPARTMENTS:
        errors["zones"] = (
            f"{MAX_DEPARTMENTS} départements, provinces ou cantons au plus par campagne."
        )
        return zones
    for item in items:
        department = _region(item, country)
        if department is None:
            errors["zones"] = unknown_region_message(item, country)
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


def criteria_to_form(criteria: Criteria) -> dict[str, str]:
    return {
        "avis_max": _text(criteria.max_reviews), "avis_min": _text(criteria.min_reviews),
        "site": criteria.website, "telephone": criteria.phone,
        "franchises": "on" if criteria.exclude_franchises else "",
    }  # fmt: skip


def request_to_form(request: CampaignRequest) -> dict[str, str]:
    """Pour pré-remplir le formulaire depuis un modèle (C18)."""
    values = {
        "nom": request.name, "metiers": ", ".join(request.trades), "nombre": str(request.target),
        "synonymes": "on" if request.synonyms_on else "", **criteria_to_form(request.criteria),
        "departements": ", ".join(z.code for z in request.zones if isinstance(z, DepartmentZone)),
        "commune": "", "ville": "", "rayon": "0",
        "pays": request.zones[0].city.country if isinstance(request.zones[0], RadiusZone)
        else request.zones[0].country,
    }  # fmt: skip
    for zone in request.zones:
        if isinstance(zone, (CityZone, RadiusZone)):
            city = zone if isinstance(zone, CityZone) else zone.city
            values.update(commune=commune_value(city), ville=city.label)
            values["rayon"] = str(zone.radius_km) if isinstance(zone, RadiusZone) else "0"
    return values
