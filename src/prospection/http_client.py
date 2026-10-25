"""Client HTTP commun aux sources et au CRM : délai court, pas de redirection.

Les erreurs réseau deviennent un message sans URL ni clé (rien de secret ne fuit).
"""

import logging
from typing import Any

import httpx

from prospection.domain.key_check import KeyCheck, no_answer

TIMEOUT_SECONDS = 10.0
logger = logging.getLogger(__name__)


GOOGLE_HOST = "places.googleapis.com"


class GoogleToFake(httpx.BaseTransport):
    """Bout en bout seulement : envoie les appels Google vers un faux Google local."""

    def __init__(self, fake_url: str, inner: httpx.BaseTransport | None = None) -> None:
        self.fake = httpx.URL(fake_url)
        self.inner = inner or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == GOOGLE_HOST:
            request.url = request.url.copy_with(
                scheme=self.fake.scheme, host=self.fake.host, port=self.fake.port
            )
            request.headers["Host"] = request.url.netloc.decode()
        return self.inner.handle_request(request)

    def close(self) -> None:
        self.inner.close()


def make_client(google_test_url: str | None = None) -> httpx.Client:
    """`google_test_url` vient d'un réglage validé (local, hors production) : voir config."""
    transport = GoogleToFake(google_test_url) if google_test_url else None
    return httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False, transport=transport)


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
