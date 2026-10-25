"""Google Places API (New) : API officielle uniquement (règle CGU)."""

import httpx

from prospection.domain.key_check import KeyCheck, unexpected
from prospection.domain.services import Service
from prospection.http_client import json_object, send

SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
LABEL = Service.GOOGLE.label


def check_google_key(client: httpx.Client, key: str) -> KeyCheck:
    """Test gratuit : recherche texte limitée aux identifiants (palier « IDs Only »)."""
    headers = {"X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id"}
    response = send(
        client, "POST", SEARCH_TEXT_URL, LABEL, headers=headers, json={"textQuery": "mairie Paris"}
    )
    if isinstance(response, KeyCheck):
        return response
    body = json_object(response)
    if body is None:
        return unexpected(LABEL)
    if response.status_code == 200:
        return KeyCheck(True, "Clé Google valide.")
    if response.status_code == 400 and "API_KEY_INVALID" in response.text:
        return KeyCheck(False, "Clé refusée par Google : vérifiez qu'elle est copiée en entier.")
    if response.status_code == 403:
        return KeyCheck(
            False,
            "Google refuse l'accès : activez « Places API (New) » et la facturation "
            "dans Google Cloud.",
        )
    return unexpected(LABEL)
