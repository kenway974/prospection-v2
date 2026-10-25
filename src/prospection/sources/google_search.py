"""Recherche Google Places (New) Text Search : API officielle uniquement (règle CGU).

Un appel = une page de 20 établissements, palier « Text Search Enterprise ».
Chaque établissement est validé ; un établissement invalide est ignoré et compté.
"""

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from prospection.domain.key_check import KeyCheck
from prospection.domain.place import Circle, Place
from prospection.http_client import json_object, send
from prospection.sources.google_models import ApiPlace, to_place
from prospection.sources.google_places import SEARCH_TEXT_URL, check_google_key_response

FIELD_MASK = ",".join(
    [
        "places.id", "places.displayName", "places.formattedAddress", "places.location",
        "places.types", "places.primaryType", "places.businessStatus",
        "places.nationalPhoneNumber", "places.internationalPhoneNumber", "places.websiteUri",
        "places.rating", "places.userRatingCount", "places.regularOpeningHours",
        "places.googleMapsUri", "places.photos", "nextPageToken",
    ]
)  # fmt: skip
PAGE_SIZE = 20


class GoogleBusy(Exception):
    """Google ne répond pas ou demande de ralentir : réessayer plus tard."""


class GoogleRejectedPage(Exception):
    """Google refuse cette requête-là (400), pas la clé : on passe à la suivante."""


class GoogleRefused(Exception):
    """Google refuse la requête (clé, API non activée…) ; le message dit quoi faire."""


@dataclass(frozen=True)
class SearchPage:
    places: list[Place]
    next_token: str | None
    skipped: int


def _body(query: str, bias: Circle | None, page_token: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "textQuery": query, "pageSize": PAGE_SIZE, "languageCode": "fr", "regionCode": "FR",
    }  # fmt: skip
    if page_token:
        body["pageToken"] = page_token
    if bias:
        center = {"latitude": bias.lat, "longitude": bias.lon}
        body["locationBias"] = {"circle": {"center": center, "radius": float(bias.radius_m)}}
    return body


def search_page(
    client: httpx.Client, key: str, query: str, bias: Circle | None, page_token: str | None
) -> SearchPage:
    headers = {"X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELD_MASK}
    response = send(
        client, "POST", SEARCH_TEXT_URL, "Google Maps", headers=headers,
        json=_body(query, bias, page_token),
    )  # fmt: skip
    if isinstance(response, KeyCheck) or response.status_code == 429:
        raise GoogleBusy
    if response.status_code >= 500:
        raise GoogleBusy
    if response.status_code == 400 and "API_KEY_INVALID" not in response.text:
        raise GoogleRejectedPage
    if response.status_code != 200:
        raise GoogleRefused(check_google_key_response(response).message)
    body = json_object(response)
    if body is None:
        raise GoogleBusy
    places, skipped = [], 0
    raw_places = body.get("places", [])
    for raw in raw_places if isinstance(raw_places, list) else []:
        try:
            places.append(to_place(ApiPlace.model_validate(raw)))
        except ValidationError:
            skipped += 1
    token = body.get("nextPageToken")
    return SearchPage(places, token if isinstance(token, str) and token else None, skipped)
