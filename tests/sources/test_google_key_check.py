"""C03 : la clé Google est testée par un appel gratuit, avec un message clair."""

import json

from prospection.domain.key_check import KeyCheck
from prospection.sources.google_places import check_google_key
from tests.fake_http import fake_client, html_reply, json_reply, timeout

KEY = "AIza-cle-de-test"


def test_C03_valid() -> None:
    client, recorder = fake_client(json_reply(200, {"places": [{"id": "abc"}]}))
    assert check_google_key(client, KEY) == KeyCheck(True, "Clé Google valide.")
    request = recorder.requests[0]
    assert str(request.url) == "https://places.googleapis.com/v1/places:searchText"
    assert request.method == "POST"
    assert request.headers["X-Goog-Api-Key"] == KEY
    assert request.headers["X-Goog-FieldMask"] == "places.id"
    assert json.loads(request.content) == {"textQuery": "mairie Paris"}


def test_C03_refused() -> None:
    body = {
        "error": {
            "code": 400,
            "status": "INVALID_ARGUMENT",
            "details": [{"reason": "API_KEY_INVALID"}],
        }
    }
    client, _ = fake_client(json_reply(400, body))
    assert check_google_key(client, KEY) == KeyCheck(
        False, "Clé refusée par Google : vérifiez qu'elle est copiée en entier."
    )


def test_C03_google_403_explains_api_activation() -> None:
    client, _ = fake_client(json_reply(403, {"error": {"status": "PERMISSION_DENIED"}}))
    assert check_google_key(client, KEY) == KeyCheck(
        False,
        "Google refuse l'accès : activez « Places API (New) » et la facturation dans Google Cloud.",
    )


def test_C03_timeout() -> None:
    client, _ = fake_client(timeout)
    assert check_google_key(client, KEY) == KeyCheck(
        False, "Google Maps ne répond pas. Réessayez dans un instant."
    )


def test_C03_unexpected_html() -> None:
    for status in (200, 500):
        client, _ = fake_client(html_reply(status))
        result = check_google_key(client, KEY)
        assert result == KeyCheck(False, "Réponse inattendue de Google Maps. Réessayez plus tard.")
        assert KEY not in result.message


def test_C03_non_ascii_key_never_crashes() -> None:
    client, _ = fake_client(json_reply(200, {}))
    result = check_google_key(client, "AIza​123")
    assert result.ok is False
