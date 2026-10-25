"""Pays proposés, villes et provinces / cantons hors de France (C121 à C123).

Données : `data/zones_etrangeres.yaml` (écrit à la main) et `data/villes_etrangeres.yaml`
(GeoNames, généré par scripts/build_foreign_cities.py).
"""

import re
from functools import cache
from importlib import resources
from typing import Any

import yaml
from pydantic import BaseModel, Field

from prospection.domain.campaign_request import CityZone, DepartmentZone
from prospection.domain.trades import normalize

MAX_CHOICES = 10
_BELGIAN_POSTAL = re.compile(r"\b(\d{4})\b")


class Region(BaseModel):
    code: str = Field(pattern=r"^[A-Z]{2,3}$")
    nom: str = Field(min_length=1, max_length=80)
    court: str = Field(min_length=1, max_length=60)
    postaux: list[tuple[int, int]] = []


class ForeignZones(BaseModel):
    pays: dict[str, str]
    regions: dict[str, list[Region]]


def _read(name: str) -> Any:
    return yaml.safe_load(resources.files("prospection.data").joinpath(name).read_text("utf-8"))


@cache
def _zones() -> ForeignZones:
    return ForeignZones.model_validate(_read("zones_etrangeres.yaml"))


@cache
def _cities() -> dict[str, list[tuple[str, str, float, float, tuple[str, ...]]]]:
    data = _read("villes_etrangeres.yaml")
    return {
        country: [(n, "" if r == "00" else r, la, lo, tuple(o)) for n, r, la, lo, o in rows]
        for country, rows in data.items()
    }


def countries() -> dict[str, str]:
    """Code → nom, France en premier."""
    return dict(_zones().pays)


def find_foreign_cities(text: str, country: str) -> list[CityZone]:
    """Nom exact (ou autre nom, ex. « Bruxelles ») d'abord, sinon les noms qui commencent ainsi."""
    wanted = normalize(text)
    if not wanted:
        return []
    exact: list[CityZone] = []
    starting: list[CityZone] = []
    for name, region, lat, lon, others in _cities().get(country, []):
        same = [n for n in (name, *others) if normalize(n) == wanted]
        if same:  # le nom tel que saisi s'il existe (« Genève » plutôt que « Geneve »)
            typed = text.strip().casefold()
            matched = next((n for n in same if n.casefold() == typed), same[0])
            exact.append(CityZone(matched, region, lat, lon, country))
        elif normalize(name).startswith(wanted):
            starting.append(CityZone(name, region, lat, lon, country))
    return (exact or starting)[:MAX_CHOICES]


def _regions(country: str) -> list[Region]:
    return _zones().regions.get(country, [])


def find_region(text: str, country: str) -> DepartmentZone | None:
    """Province (Belgique) ou canton (Suisse, Luxembourg) par code ou par nom."""
    wanted = normalize(text)
    for region in _regions(country):
        if wanted in {normalize(region.code), normalize(region.nom), normalize(region.court)}:
            return DepartmentZone(region.code, region.nom, country)
    return None


def region_names(country: str) -> dict[str, str]:
    return {r.code: r.nom for r in _regions(country)}


def postal_region(address: str, country: str) -> str | None:
    """Province belge d'après le code postal de l'adresse ; None ailleurs ou sans code."""
    codes = [int(c) for c in _BELGIAN_POSTAL.findall(address)] if country == "BE" else []
    for region in _regions(country) if codes else []:
        if any(low <= codes[-1] <= high for low, high in region.postaux):
            return region.code
    return None
