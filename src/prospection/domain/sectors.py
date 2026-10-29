"""Secteurs : un choix remplit les métiers avec tous les mots-clés du secteur (C132).

Les secteurs vivent dans le fichier de données `data/secteurs.yaml` (validé au chargement).
Source : prospection-bot/target_segments.py (530ba12).
"""

from functools import cache
from importlib import resources

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from prospection.domain.trades import MAX_TRADES


class InvalidSectorFile(ValueError):
    """Le fichier des secteurs est mal formé."""


class Sector(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(pattern=r"^[a-z_]+$")
    label: str = Field(min_length=1)
    keywords: tuple[str, ...] = Field(min_length=1, max_length=MAX_TRADES)


class SectorGroup(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str = Field(min_length=1)
    sectors: tuple[Sector, ...] = Field(min_length=1)


_GROUPS = TypeAdapter(tuple[SectorGroup, ...])


def parse_sectors(text: str) -> tuple[SectorGroup, ...]:
    try:
        groups = _GROUPS.validate_python(yaml.safe_load(text))
    except (yaml.YAMLError, ValidationError) as error:
        raise InvalidSectorFile(f"Fichier des secteurs invalide : {error}") from None
    ids = [s.id for g in groups for s in g.sectors]
    if len(set(ids)) != len(ids):
        raise InvalidSectorFile("Fichier des secteurs invalide : identifiant en double.")
    return groups


@cache
def load_sectors() -> tuple[SectorGroup, ...]:
    """Secteurs livrés avec l'app, lus une seule fois."""
    return parse_sectors(
        resources.files("prospection.data").joinpath("secteurs.yaml").read_text("utf-8")
    )
