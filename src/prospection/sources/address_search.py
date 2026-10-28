"""Adresse → position, par l'API Adresse officielle (api-adresse.data.gouv.fr, gratuite, sans
clé) pour le mode Terrain (C113). Réponse validée ; rien de trouvé ou service muet : None."""

from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.key_check import KeyCheck
from prospection.domain.place import clip
from prospection.http_client import json_object, send

SEARCH_URL = "https://api-adresse.data.gouv.fr/search/"


@dataclass(frozen=True)
class Located:
    label: str
    lat: float
    lon: float


class _Geometry(BaseModel):
    coordinates: tuple[float, float]  # longitude, latitude


class _Properties(BaseModel):
    label: str


class _Feature(BaseModel):
    geometry: _Geometry
    properties: _Properties


def find_address(client: httpx.Client, text: str) -> Located | None:
    query = " ".join(text.split())[:200]
    if len(query) < 3:
        return None
    response = send(client, "GET", SEARCH_URL, "API Adresse", params={"q": query, "limit": 1})
    if isinstance(response, KeyCheck) or response.status_code != 200:
        return None
    features = (json_object(response) or {}).get("features")
    try:
        feature = (
            _Feature.model_validate(features[0])
            if isinstance(features, list) and features
            else None
        )
    except ValidationError:
        return None
    if feature is None:
        return None
    lon, lat = feature.geometry.coordinates
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return Located(clip(feature.properties.label, 120) or query, lat, lon)
