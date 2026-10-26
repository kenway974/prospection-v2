"""C13 : trouver la commune (et son centre) via l'API géo officielle, gratuite."""

import pytest

from prospection.domain.campaign_request import CityZone
from prospection.sources.geo_communes import GeoUnavailable, find_communes
from tests.fake_http import fake_client, html_reply, json_reply

SAINT_DENIS = [
    {
        "nom": "Saint-Denis",
        "code": "93066",
        "codeDepartement": "93",
        "centre": {"type": "Point", "coordinates": [2.35, 48.93]},
    },
    {
        "nom": "Saint-Denis",
        "code": "97411",
        "codeDepartement": "974",
        "centre": {"type": "Point", "coordinates": [55.45, -20.88]},
    },
]


def test_communes_ambiguous_name_returns_all_with_department() -> None:
    client, recorder = fake_client(json_reply(200, SAINT_DENIS))
    communes = find_communes(client, "Saint-Denis")
    assert communes == [
        CityZone("Saint-Denis", "93066", 48.93, 2.35),
        CityZone("Saint-Denis", "97411", -20.88, 55.45),
    ]
    assert [c.label for c in communes] == ["Saint-Denis (93)", "Saint-Denis (974)"]
    url = recorder.requests[0].url
    assert url.host == "geo.api.gouv.fr" and url.path == "/communes"
    assert url.params["nom"] == "Saint-Denis"
    assert url.params["fields"] == "nom,code,codeDepartement,centre"


def test_unknown_commune_returns_empty() -> None:
    client, _ = fake_client(json_reply(200, []))
    assert find_communes(client, "Atlantide") == []


def test_blank_name_makes_no_call() -> None:
    client, recorder = fake_client(json_reply(200, []))
    assert find_communes(client, "  ") == []
    assert recorder.requests == []


def test_bad_answer_raises_unavailable() -> None:
    client, _ = fake_client(html_reply(200))
    with pytest.raises(GeoUnavailable):
        find_communes(client, "Lyon")
