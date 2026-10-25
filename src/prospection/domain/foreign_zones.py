"""Pays proposés, villes et provinces / cantons hors de France (C121 à C123).

Données lues et validées par domain/foreign_data.py.
"""

__all__ = ["InvalidZoneFile", "parse_cities"]  # pour les tests des fichiers de données

import re

from prospection.domain.campaign_request import CityZone, DepartmentZone
from prospection.domain.foreign_data import InvalidZoneFile, Region, cities, parse_cities, zones
from prospection.domain.trades import normalize

MAX_CHOICES = 10
_BELGIAN_POSTAL = re.compile(r"\b(\d{4})\b")


def countries() -> dict[str, str]:
    """Code → nom, France en premier."""
    return {code: country.nom for code, country in zones().pays.items()}


def find_foreign_cities(text: str, country: str) -> list[CityZone]:
    """Nom exact (ou autre nom, ex. « Bruxelles ») d'abord, sinon les noms qui commencent ainsi."""
    wanted = normalize(text)
    if not wanted:
        return []
    exact: list[CityZone] = []
    starting: list[CityZone] = []
    for city in cities().get(country, []):
        name, region, lat, lon, others = city.name, city.region, city.lat, city.lon, city.others
        same = [n for n in (name, *others) if normalize(n) == wanted]
        if same:  # le nom tel que saisi s'il existe (« Genève » plutôt que « Geneve »)
            typed = text.strip().casefold()
            matched = next((n for n in same if n.casefold() == typed), same[0])
            exact.append(CityZone(matched, region, lat, lon, country))
        elif normalize(name).startswith(wanted):
            starting.append(CityZone(name, region, lat, lon, country))
    return (exact or starting)[:MAX_CHOICES]


def resolve_foreign_city(name: str, code: str, country: str) -> CityZone | None:
    """La ville telle qu'elle est dans les données, ou None (valeur de formulaire trafiquée)."""
    found = find_foreign_cities(name, country)
    return next((c for c in found if (c.name, c.code) == (name, code)), None)


def _regions(country: str) -> list[Region]:
    return zones().regions.get(country, [])


def find_region(text: str, country: str) -> DepartmentZone | None:
    """Province (Belgique) ou canton (Suisse, Luxembourg) par code ou par nom."""
    wanted = normalize(text)
    for region in _regions(country):
        names = (region.code, region.nom, region.court, *region.autres)
        if wanted in {normalize(n) for n in names}:
            return DepartmentZone(region.code, region.nom, country)
    return None


def known_region(text: str, country: str) -> str | None:
    """Code du canton nommé par Google (« VD », « Vaud »), ou None s'il n'est pas reconnu."""
    region = find_region(text, country) if text else None
    return region.code if region else None


def postal_region(address: str, country: str) -> str | None:
    """Province belge d'après le code postal de l'adresse ; None ailleurs ou sans code."""
    codes = [int(c) for c in _BELGIAN_POSTAL.findall(address)] if country == "BE" else []
    for region in _regions(country) if codes else []:
        if any(low <= codes[-1] <= high for low, high in region.postaux):
            return region.code
    return None


def city_choice_label(city: CityZone) -> str:
    """Ex. « Liège (Wallonie, Belgique) », « Genève (Genève, Suisse) »."""
    country = zones().pays[city.country]
    region = country.regions_des_villes.get(city.code) or next(
        (r.court for r in _regions(city.country) if r.code == city.code), ""
    )
    return f"{city.name} ({region}, {country.nom})" if region else f"{city.name} ({country.nom})"


def unknown_region_message(text: str, country: str) -> str:
    data = zones().pays[country]
    if not data.inconnu:
        return f"{data.nom} n'a ni province ni canton : choisissez seulement la ville."
    return f"{data.inconnu} {data.dans} : {text.strip()}. Exemple : {data.exemple}."
