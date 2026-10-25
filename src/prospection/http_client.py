"""Client HTTP commun aux sources et au CRM : délai court, pas de redirection.

Les erreurs réseau deviennent un message sans URL ni clé (rien de secret ne fuit).
"""

import logging
from typing import Any

import httpx

from prospection.domain.key_check import KeyCheck, no_answer

TIMEOUT_SECONDS = 10.0
logger = logging.getLogger(__name__)


def make_client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False)


def send(
    client: httpx.Client, method: str, url: str, service_label: str, **kwargs: Any
) -> httpx.Response | KeyCheck:
    """Envoie la requête ; rend la réponse, ou un KeyCheck d'échec si le service est muet."""
    try:
        return client.request(method, url, **kwargs)
    except (httpx.HTTPError, UnicodeError) as error:
        logger.warning("%s injoignable : %s", service_label, type(error).__name__)
        return no_answer(service_label)


def json_object(response: httpx.Response) -> dict[str, Any] | None:
    """Corps JSON s'il s'agit bien d'un objet, sinon None (HTML, texte, liste…)."""
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None
