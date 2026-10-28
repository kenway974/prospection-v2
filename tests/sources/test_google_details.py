"""C76 : fiche relue chez Google (Place Details), réponse validée."""

import pytest

from prospection.sources.google_details import DETAILS_MASK, place_details
from prospection.sources.google_search import GoogleBusy, GoogleRefused
from tests.application.campaign_helpers import api_place
from tests.fake_http import fake_client, json_reply


def test_C76_place_read_with_the_same_fields() -> None:
    client, seen = fake_client(json_reply(200, {**api_place(1), "websiteUri": "https://a.fr"}))
    place = place_details(client, "AIza-test", "place-1")
    assert place is not None and place.website == "https://a.fr"
    request = seen.requests[0]
    assert request.url.path == "/v1/places/place-1" and "nextPageToken" not in DETAILS_MASK
    assert request.headers["X-Goog-FieldMask"].startswith("id,displayName")


def test_C76_unknown_place_busy_or_refused() -> None:
    gone, _ = fake_client(json_reply(404, {"error": {"status": "NOT_FOUND"}}))
    assert place_details(gone, "k", "place-1") is None
    forged, calls = fake_client(json_reply(200, {}))
    with pytest.raises(ValueError):
        place_details(forged, "k", "../../autre")
    assert calls.requests == []
    mask_refused = fake_client(json_reply(400, {"error": {"status": "INVALID_ARGUMENT"}}))[0]
    with pytest.raises(GoogleRefused):  # jamais « plus trouvé » pour une requête refusée
        place_details(mask_refused, "k", "place-1")
    with pytest.raises(GoogleBusy):
        place_details(fake_client(json_reply(503, {}))[0], "k", "place-1")
    with pytest.raises(GoogleBusy):
        place_details(fake_client(json_reply(200, {"id": 3}))[0], "k", "place-1")
    with pytest.raises(GoogleRefused):
        place_details(fake_client(json_reply(403, {"error": {"status": "PERMISSION_DENIED"}}))[0],
                      "k", "place-1")  # fmt: skip
