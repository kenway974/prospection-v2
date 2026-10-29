"""Formulaire Recherche <-> demande de campagne (traduction seulement, sans règle métier)."""

import re
from dataclasses import dataclass, field
from typing import cast

from prospection.domain.campaign_request import (
    CityZone,
    DepartmentZone,
    RadiusZone,
    RawRequest,
    Zone,
)
from prospection.domain.criteria import Criteria, SiteChoice
from prospection.domain.departments import find_department
from prospection.domain.foreign_zones import (
    countries,
    find_region,
    resolve_foreign_city,
    unknown_region_message,
)
from prospection.domain.place import clip
from prospection.domain.registry import SOURCES
from prospection.domain.site_criteria import SITE_CHOICES
from prospection.domain.trades import MAX_TRADES, split_trades

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


def _site_choice(value: str | None) -> SiteChoice:
    return cast("SiteChoice", value) if value in SITE_CHOICES else "any"


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
        created_within_days=_int(form.get("jours", ""), 0) or 0,
        max_workforce=form.get("effectif_max") or None,
        max_site_score=_int(form.get("score_site_max", ""), None),
        no_form=_site_choice(form.get("sans_formulaire")),
        no_https=_site_choice(form.get("sans_https")),
        not_mobile=_site_choice(form.get("non_mobile")),
    )
    raw = RawRequest(
        name=form.get("nom", "")[:100],
        trades=split_trades(form.get("metiers", ""))[: MAX_TRADES + 1],  # au-delà : refusé
        zones=_zones(form, errors),
        target=_int(form.get("nombre", ""), 0) or 0,
        criteria=criteria,
        synonyms_on=form.get("synonymes") == "on",
        sources=tuple(s for s in SOURCES if form.get(f"source_{s}") == "on"),
    )
    return ParsedForm(raw, errors)
