"""Règle 5 : seuls les liens web ordinaires venant de Google sont gardés."""

import pytest

from prospection.sources.google_search import search_page
from tests.fake_http import fake_client, json_reply
from tests.sources.test_google_search import KEY, place


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "data:text/html,x", "//ailleurs.example", "https://" + "x" * 2100],
)
def test_only_plain_web_links_kept(url: str) -> None:
    body = {"places": [place(websiteUri=url, googleMapsUri=url)]}
    client, _ = fake_client(json_reply(200, body))
    found = search_page(client, KEY, "q", None, None).places[0]
    assert (found.website, found.maps_url) == (None, None)


def test_web_links_kept_whole() -> None:
    url = "https://www.atelier-bois.fr/" + "a" * 400
    client, _ = fake_client(json_reply(200, {"places": [place(websiteUri=url)]}))
    assert search_page(client, KEY, "q", None, None).places[0].website == url
