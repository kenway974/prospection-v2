"""C13 : la ville se choisit dans la liste officielle des communes."""

import httpx

from prospection.application.search_screen import find_city
from tests.fake_http import fake_client


def test_C13_unknown_city_says_what_to_do() -> None:
    client, _ = fake_client(lambda r: httpx.Response(200, json=[]))
    assert find_city(client, "Nulle-part").problem == (
        "Aucune commune de ce nom. Vérifiez l'orthographe."
    )


def test_C13_commune_service_down_says_to_retry() -> None:
    client, _ = fake_client(lambda r: httpx.Response(503, text="panne"))
    result = find_city(client, "Lyon")
    assert result.choices == []
    assert result.problem == "Le service des communes ne répond pas. Réessayez dans un instant."
