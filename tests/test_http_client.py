"""Le client HTTP commun : délai court, aucune redirection suivie."""

from prospection.domain.key_check import KeyCheck
from prospection.http_client import TIMEOUT_SECONDS, make_client
from prospection.sources.google_places import check_google_key
from tests.fake_http import fake_client


def test_client_has_10s_timeout_and_never_follows_redirects() -> None:
    client = make_client()
    assert TIMEOUT_SECONDS == 10.0
    assert client.timeout.connect == 10.0 and client.timeout.read == 10.0
    assert client.follow_redirects is False


def test_redirect_is_an_unexpected_answer() -> None:
    import httpx

    client, _ = fake_client(
        lambda request: httpx.Response(302, headers={"Location": "https://ailleurs.example"})
    )
    assert check_google_key(client, "AIza-x") == KeyCheck(
        False, "Réponse inattendue de Google Maps. Réessayez plus tard."
    )
