"""Lecture et validation des fichiers de données des pays (C121, C122).

`data/zones_etrangeres.yaml` (écrit à la main) et `data/villes_etrangeres.yaml` (GeoNames,
généré par scripts/build_foreign_cities.py). Un fichier invalide est refusé au chargement.
"""

from functools import cache
from importlib import resources
from typing import Annotated

import yaml
from pydantic import BaseModel, Field, StringConstraints, ValidationError

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class InvalidZoneFile(ValueError):
    pass


class Country(BaseModel):
    nom: Text
    dans: Text
    inconnu: str = ""
    exemple: str = ""
    regions_des_villes: dict[str, Text] = {}


class Region(BaseModel):
    code: str = Field(pattern=r"^[A-Z]{2,3}$")
    nom: Text
    court: Text
    autres: list[Text] = []
    postaux: list[tuple[int, int]] = []


class ForeignZones(BaseModel):
    pays: dict[CountryCode, Country]
    regions: dict[CountryCode, list[Region]]


class City(BaseModel):
    name: Text
    region: str = Field(pattern=r"^[A-Z0-9]{0,3}$")
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    others: tuple[Text, ...]


def _parse[T: BaseModel](model: type[T], text: str) -> T:
    try:
        return model.model_validate(yaml.safe_load(text))
    except (yaml.YAMLError, ValidationError) as error:
        raise InvalidZoneFile(f"Fichier de zones invalide : {error}") from None


class _Cities(BaseModel):
    rows: dict[CountryCode, list[tuple[Text, str, float, float, list[Text]]]]


def parse_cities(text: str) -> dict[str, list[City]]:
    """Lignes [nom, région, latitude, longitude, autres noms], par pays."""
    try:
        raw = _Cities.model_validate({"rows": yaml.safe_load(text)}).rows
        return {
            country: [
                City(name=n, region="" if r == "00" else r, lat=la, lon=lo, others=tuple(o))
                for n, r, la, lo, o in rows
            ]
            for country, rows in raw.items()
        }
    except (yaml.YAMLError, ValidationError) as error:
        raise InvalidZoneFile(f"Fichier des villes invalide : {error}") from None


def _read(name: str) -> str:
    return resources.files("prospection.data").joinpath(name).read_text("utf-8")


@cache
def zones() -> ForeignZones:
    return _parse(ForeignZones, _read("zones_etrangeres.yaml"))


@cache
def cities() -> dict[str, list[City]]:
    return parse_cities(_read("villes_etrangeres.yaml"))
