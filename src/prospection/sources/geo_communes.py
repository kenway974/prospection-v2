"""Communes françaises et leur centre via geo.api.gouv.fr (API officielle, gratuite)."""

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.campaign_request import CityZone
from prospection.domain.key_check import KeyCheck
from prospection.http_client import send

COMMUNES_URL = "https://geo.api.gouv.fr/communes"


class GeoUnavailable(Exception):
    """Le service des communes ne répond pas comme prévu."""


class _Centre(BaseModel):
    coordinates: tuple[float, float]


class _Commune(BaseModel):
    nom: str
    code: str
    centre: _Centre


def find_communes(client: httpx.Client, name: str) -> list[CityZone]:
    """Communes portant ce nom (les plus peuplées d'abord), 5 au plus."""
    if not name.strip():
        return []
    params = {
        "nom": name.strip()[:100],
        "fields": "nom,code,codeDepartement,centre",
        "boost": "population",
        "limit": "5",
    }
    response = send(client, "GET", COMMUNES_URL, "Service des communes", params=params)
    if isinstance(response, KeyCheck) or response.status_code != 200:
        raise GeoUnavailable
    try:
        communes = [_Commune.model_validate(c) for c in response.json()]
    except (ValueError, ValidationError, TypeError):
        raise GeoUnavailable from None
    return [
        CityZone(c.nom[:100], c.code[:5], c.centre.coordinates[1], c.centre.coordinates[0])
        for c in communes
    ]
