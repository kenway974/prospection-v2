"""Fiche d'un établissement relue chez Google (Place Details, API officielle) pour la mise à
jour d'une campagne passée (C76). Mêmes champs que la recherche, réponse validée."""

import re

import httpx
from pydantic import ValidationError

from prospection.domain.key_check import KeyCheck
from prospection.domain.place import Place
from prospection.http_client import json_object, send
from prospection.sources.google_models import ApiPlace, to_place
from prospection.sources.google_places import check_google_key_response
from prospection.sources.google_search import FIELD_MASK, GoogleBusy, GoogleRefused

DETAILS_URL = "https://places.googleapis.com/v1/places/"
DETAILS_MASK = ",".join(
    f.removeprefix("places.") for f in FIELD_MASK.split(",") if f != "nextPageToken"
)
_PLACE_ID = re.compile(r"[A-Za-z0-9_-]{1,300}")


def valid_place_id(place_id: str) -> bool:
    """Identifiant Google utilisable tel quel dans l'adresse (jamais de chemin forgé)."""
    return _PLACE_ID.fullmatch(place_id) is not None


def place_details(client: httpx.Client, key: str, place_id: str) -> Place | None:
    """La fiche, ou None si Google ne connaît plus l'établissement (404). Toute autre
    erreur 4xx (masque refusé, clé…) lève GoogleRefused : rien n'est dit « fermé » à tort."""
    if not valid_place_id(place_id):
        raise ValueError("identifiant Google invalide")
    headers = {"X-Goog-Api-Key": key, "X-Goog-FieldMask": DETAILS_MASK}
    response = send(
        client, "GET", DETAILS_URL + place_id, "Google Maps", headers=headers,
        params={"languageCode": "fr"},
    )  # fmt: skip
    if isinstance(response, KeyCheck) or response.status_code == 429:
        raise GoogleBusy
    if response.status_code >= 500:
        raise GoogleBusy
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise GoogleRefused(check_google_key_response(response).message)
    body = json_object(response)
    if body is None:
        raise GoogleBusy
    try:
        return to_place(ApiPlace.model_validate(body))
    except ValidationError:
        raise GoogleBusy from None
