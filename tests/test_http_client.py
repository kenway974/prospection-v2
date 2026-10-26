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


def test_google_calls_go_to_local_fake_only_when_asked() -> None:
    import httpx

    from prospection.http_client import ServicesToFake

    seen: list[str] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={})

    transport = ServicesToFake("http://127.0.0.1:8099", httpx.MockTransport(record))
    with httpx.Client(transport=transport) as client:
        client.post("https://places.googleapis.com/v1/places:searchText")
        client.get("https://recherche-entreprises.api.gouv.fr/search?q=x")
        client.get("https://api.insee.fr/api-sirene/3.11/siret")
        client.get("https://api.notion.com/v1/users/me")
    assert seen == [
        "http://127.0.0.1:8099/v1/places:searchText",
        "http://127.0.0.1:8099/search?q=x",
        "http://127.0.0.1:8099/api-sirene/3.11/siret",
        "https://api.notion.com/v1/users/me",
    ]
    assert make_client()._transport.__class__ is not ServicesToFake
