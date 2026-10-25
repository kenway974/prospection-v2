"""API Sirene de l'INSEE (registre officiel des entreprises)."""

import httpx

from prospection.domain.key_check import KeyCheck, unexpected
from prospection.domain.services import Service
from prospection.http_client import json_object, send

BASE_URL = "https://api.insee.fr/api-sirene/3.11"
LABEL = Service.INSEE.label


def check_insee_key(client: httpx.Client, key: str) -> KeyCheck:
    """Test gratuit : état du service Sirene."""
    headers = {"X-INSEE-Api-Key-Integration": key, "Accept": "application/json"}
    response = send(client, "GET", f"{BASE_URL}/informations", LABEL, headers=headers)
    if isinstance(response, KeyCheck):
        return response
    if response.status_code in (401, 403):
        return KeyCheck(
            False,
            "Clé refusée par l'INSEE : vérifiez-la sur portail-api.insee.fr et que "
            "l'application est abonnée à l'API Sirene.",
        )
    if response.status_code == 200 and json_object(response) is not None:
        return KeyCheck(True, "Clé Sirène valide.")
    return unexpected(LABEL)
