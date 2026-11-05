"""Open PageRank (DomCop) : autorité d'un domaine de 0 à 10, gratuite avec une clé (C143).

API officielle, une requête par domaine demandé ; la réponse est validée. Un domaine absent
de l'index n'a aucune autorité (0). Service muet ou réponse étrange : AuthorityUnavailable.
"""

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.key_check import KeyCheck, unexpected
from prospection.domain.services import Service
from prospection.http_client import json_object, send

API_URL = "https://openpagerank.com/api/v1.0/getPageRank"
LABEL = Service.OPENPAGERANK.label


class AuthorityUnavailable(Exception):
    """Open PageRank ne répond pas ou répond de façon inattendue : réessayer plus tard."""


class _Item(BaseModel):
    status_code: int
    page_rank_decimal: float | str | None = None


class _Answer(BaseModel):
    response: list[_Item]


def _ask(client: httpx.Client, key: str, domain: str) -> httpx.Response | KeyCheck:
    headers = {"API-OPR": key, "Accept": "application/json"}
    return send(client, "GET", API_URL, LABEL, headers=headers, params={"domains[]": domain})


def page_rank(client: httpx.Client, key: str, domain: str) -> float:
    response = _ask(client, key, domain)
    if isinstance(response, KeyCheck) or response.status_code != 200:
        raise AuthorityUnavailable
    try:
        items = _Answer.model_validate(json_object(response)).response
    except ValidationError:
        raise AuthorityUnavailable from None
    if not items:
        raise AuthorityUnavailable
    rank = items[0].page_rank_decimal if items[0].status_code == 200 else 0
    try:
        return min(max(float(rank or 0), 0.0), 10.0)
    except ValueError:
        return 0.0


def check_openpagerank_key(client: httpx.Client, key: str) -> KeyCheck:
    """Test gratuit : autorité d'un domaine connu."""
    response = _ask(client, key, "google.com")
    if isinstance(response, KeyCheck):
        return response
    if response.status_code in (401, 403):
        return KeyCheck(False, "Clé refusée par Open PageRank : vérifiez-la sur openpagerank.com.")
    if response.status_code == 200 and json_object(response) is not None:
        return KeyCheck(True, "Clé Open PageRank valide.")
    return unexpected(LABEL)
