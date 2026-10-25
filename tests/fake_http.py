"""Faux serveur HTTP pour les tests : aucun appel réseau réel."""

from collections.abc import Callable

import httpx

Handler = Callable[[httpx.Request], httpx.Response]


class Recorder:
    """Garde les requêtes reçues et répond avec le gestionnaire donné."""

    def __init__(self, handler: Handler) -> None:
        self.requests: list[httpx.Request] = []
        self._handler = handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def fake_client(handler: Handler) -> tuple[httpx.Client, Recorder]:
    recorder = Recorder(handler)
    return httpx.Client(transport=httpx.MockTransport(recorder)), recorder


def json_reply(status: int, body: object) -> Handler:
    return lambda request: httpx.Response(status, json=body)


def html_reply(status: int) -> Handler:
    return lambda request: httpx.Response(status, text="<html>erreur</html>")


def timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectTimeout("délai dépassé", request=request)
