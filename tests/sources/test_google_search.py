"""C42, C43 : lecture des fiches Google Maps (API officielle), réponses validées."""

import json

import httpx
import pytest

from prospection.domain.place import Circle
from prospection.sources.google_search import FIELD_MASK, GoogleBusy, GoogleRefused, search_page
from tests.fake_http import fake_client, json_reply, timeout

KEY = "AIza-cle"


def place(**changes: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "ChIJ1",
        "displayName": {"text": "Atelier Bois & Plan"},
        "formattedAddress": "12 rue des Lilas, 97400 Saint-Denis",
        "location": {"latitude": -20.88, "longitude": 55.45},
        "types": ["furniture_store", "store"],
        "primaryType": "furniture_store",
        "businessStatus": "OPERATIONAL",
        "nationalPhoneNumber": "0692 12 34 56",
        "internationalPhoneNumber": "+262 692 12 34 56",
        "rating": 4.8,
        "userRatingCount": 4,
        "regularOpeningHours": {"weekdayDescriptions": ["lundi: 08:00-18:00"]},
        "googleMapsUri": "https://maps.google.com/?cid=1",
        "photos": [
            {"authorAttributions": [{"displayName": "Atelier Bois & Plan"}]},
            {"authorAttributions": [{"displayName": "Marie D."}]},
        ],
    }
    base.update(changes)
    return base


def test_C42_fields_parsed() -> None:
    client, _ = fake_client(json_reply(200, {"places": [place()]}))
    result = search_page(client, KEY, "cuisiniste", None, None)
    found = result.places[0]
    assert (found.place_id, found.name, found.phone, found.website) == (
        "ChIJ1",
        "Atelier Bois & Plan",
        "+262 692 12 34 56",
        None,
    )
    assert (found.rating, found.review_count, found.business_status) == (4.8, 4, "OPERATIONAL")
    assert found.opening_hours == ("lundi: 08:00-18:00",)
    assert found.maps_url == "https://maps.google.com/?cid=1"
    assert result.next_token is None and result.skipped == 0


def test_exact_field_mask_and_page_size_sent() -> None:
    client, recorder = fake_client(json_reply(200, {"places": []}))
    search_page(client, KEY, "fleuriste", Circle(-20.88, 55.45, 15_000), "tok")
    request = recorder.requests[0]
    assert str(request.url) == "https://places.googleapis.com/v1/places:searchText"
    assert request.headers["X-Goog-FieldMask"] == FIELD_MASK
    assert "places.websiteUri" in FIELD_MASK and FIELD_MASK.endswith("nextPageToken")
    body = json.loads(request.content)
    assert body == {
        "textQuery": "fleuriste",
        "pageSize": 20,
        "languageCode": "fr",
        "regionCode": "FR",
        "pageToken": "tok",
        "locationBias": {
            "circle": {"center": {"latitude": -20.88, "longitude": 55.45}, "radius": 15000.0}
        },
    }


def test_C43_photo_count_and_owner_estimate() -> None:
    client, _ = fake_client(
        json_reply(
            200,
            {
                "places": [
                    place(),
                    place(id="2", photos=[{"authorAttributions": [{"displayName": "Client"}]}]),
                    place(id="3", photos=[]),
                ]
            },
        )
    )
    estimates = [
        (p.photo_count, p.owner_photo_estimate)
        for p in search_page(client, KEY, "q", None, None).places
    ]
    assert estimates == [
        (2, "probable propriétaire"),
        (1, "clients seulement"),
        (0, "inconnu"),
    ]


def test_invalid_place_skipped_and_counted() -> None:
    body = {"places": [place(), {"id": "sans-nom"}, "pas un objet"], "nextPageToken": "p2"}
    client, _ = fake_client(json_reply(200, body))
    result = search_page(client, KEY, "q", None, None)
    assert [p.place_id for p in result.places] == ["ChIJ1"]
    assert (result.skipped, result.next_token) == (2, "p2")


def test_long_texts_are_truncated() -> None:
    client, _ = fake_client(json_reply(200, {"places": [place(displayName={"text": "x" * 1000})]}))
    assert len(search_page(client, KEY, "q", None, None).places[0].name) == 300


@pytest.mark.parametrize("status", [429, 500, 503])
def test_busy_statuses_raise_busy(status: int) -> None:
    client, _ = fake_client(json_reply(status, {}))
    with pytest.raises(GoogleBusy):
        search_page(client, KEY, "q", None, None)


def test_network_error_raises_busy() -> None:
    client, _ = fake_client(timeout)
    with pytest.raises(GoogleBusy):
        search_page(client, KEY, "q", None, None)


def test_403_raises_refused_with_message() -> None:
    client, _ = fake_client(json_reply(403, {"error": {"status": "PERMISSION_DENIED"}}))
    with pytest.raises(GoogleRefused) as error:
        search_page(client, KEY, "q", None, None)
    assert "Places API (New)" in str(error.value)
    assert KEY not in str(error.value)


def test_unreadable_body_raises_busy() -> None:
    client, _ = fake_client(lambda request: httpx.Response(200, text="<html>"))
    with pytest.raises(GoogleBusy):
        search_page(client, KEY, "q", None, None)
