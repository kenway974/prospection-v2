"""C03 : la clé Sirène (INSEE) est testée, avec un message clair."""

from prospection.domain.key_check import KeyCheck
from prospection.sources.insee import check_insee_key
from tests.fake_http import fake_client, html_reply, json_reply, timeout

KEY = "cle-insee-de-test"


def test_C03_valid() -> None:
    client, recorder = fake_client(json_reply(200, {"etatService": "UP"}))
    assert check_insee_key(client, KEY) == KeyCheck(True, "Clé Sirène valide.")
    request = recorder.requests[0]
    assert str(request.url) == "https://api.insee.fr/api-sirene/3.11/informations"
    assert request.method == "GET"
    assert request.headers["X-INSEE-Api-Key-Integration"] == KEY


def test_C03_refused() -> None:
    for status in (401, 403):
        client, _ = fake_client(json_reply(status, {"message": "Invalid key"}))
        assert check_insee_key(client, KEY) == KeyCheck(
            False,
            "Clé refusée par l'INSEE : vérifiez-la sur portail-api.insee.fr et que "
            "l'application est abonnée à l'API Sirene.",
        )


def test_C03_timeout() -> None:
    client, _ = fake_client(timeout)
    assert check_insee_key(client, KEY) == KeyCheck(
        False, "Sirène (INSEE) ne répond pas. Réessayez dans un instant."
    )


def test_C03_unexpected_html() -> None:
    client, _ = fake_client(html_reply(502))
    assert check_insee_key(client, KEY) == KeyCheck(
        False, "Réponse inattendue de Sirène (INSEE). Réessayez plus tard."
    )
