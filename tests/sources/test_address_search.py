"""C113 : une adresse saisie devient une position (API Adresse officielle, gratuite)."""

import httpx

from prospection.sources.address_search import find_address
from tests.fake_http import fake_client, json_reply, timeout

BELLECOUR = {"label": "Place Bellecour 69002 Lyon", "score": 0.9}
FOUND = {"features": [{"geometry": {"coordinates": [4.8357, 45.764]}, "properties": BELLECOUR}]}


def test_C113_address_located() -> None:
    client, recorder = fake_client(json_reply(200, FOUND))
    found = find_address(client, "place bellecour lyon")
    assert found is not None and (found.lat, found.lon) == (45.764, 4.8357)
    assert found.label == "Place Bellecour 69002 Lyon"
    assert recorder.requests[0].url.params["limit"] == "1"


def test_unknown_or_unreachable_address_is_none() -> None:
    assert find_address(fake_client(json_reply(200, {"features": []}))[0], "zzz") is None
    assert find_address(fake_client(timeout)[0], "place bellecour") is None
    client, recorder = fake_client(lambda r: httpx.Response(200, json=FOUND))
    assert find_address(client, "  ") is None and recorder.requests == []
