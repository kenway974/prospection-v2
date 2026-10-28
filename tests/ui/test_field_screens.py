"""C113 à C115 : écrans Terrain."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.domain.campaign_request import InvalidRequest
from prospection.ui import routes_field
from prospection.ui.deps import get_http_client
from tests.application.test_field_tour import with_stops
from tests.fake_http import fake_client, json_reply
from tests.sources.test_address_search import FOUND
from tests.ui.test_call_screens import client, text
from tests.ui.test_search_form import ORIGIN

__all__ = ["client"]  # fixture partagée


def test_C113_form_offers_my_position_or_an_address(client: TestClient) -> None:
    page = text(client.get("/terrain"))
    assert "Utiliser ma position" in page and 'name="adresse"' in page
    assert 'name="avis_max"' in page and 'name="sans_site"' in page and 'name="ouvert"' in page


def test_C113_search_from_my_position_starts_a_tour(client: TestClient) -> None:
    form = {"lat": "45.764", "lon": "4.8357", "metiers": "boulangerie", "rayon": "1",
            "avis_max": "20", "nombre": "10"}  # fmt: skip
    response = client.post("/terrain", data=form, headers=ORIGIN, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"].startswith("/terrain/")


def test_C113_address_located_or_said_unknown(client: TestClient) -> None:
    fake, _ = fake_client(json_reply(200, FOUND))
    client.app.dependency_overrides[get_http_client] = lambda: fake  # type: ignore[attr-defined]
    ok = client.post("/terrain", data={"adresse": "place bellecour"}, headers=ORIGIN,
                     follow_redirects=False)  # fmt: skip
    assert ok.status_code == 303
    nothing, _ = fake_client(json_reply(200, {"features": []}))
    client.app.dependency_overrides[get_http_client] = lambda: nothing  # type: ignore[attr-defined]
    bad = client.post("/terrain", data={"adresse": "zzz zzz"}, headers=ORIGIN)
    assert bad.status_code == 400 and "Adresse introuvable" in text(bad)


def test_C114_C115_tour_with_route_and_one_gesture(client: TestClient, campaign_db: Engine) -> None:
    campaign_id = with_stops(campaign_db)
    page = text(client.get(f"/terrain/{campaign_id}"))
    assert "Ouvrir l'itinéraire" in page and "https://www.google.com/maps/dir/" in page
    assert page.index("Boutique 2") < page.index("Boutique 3") < page.index("Boutique 1")
    with campaign_db.connect() as conn:
        first = conn.exec_driver_sql("SELECT id FROM prospects WHERE place_id = 't2'").scalar_one()
    done = client.post(f"/terrain/arret/{first}", data={"choix": "interesse"}, headers=ORIGIN,
                       follow_redirects=False)  # fmt: skip
    assert done.status_code in (200, 303)
    assert "Intéressé" in text(client.get(f"/terrain/{campaign_id}"))


def test_C113_open_now_box_carried_to_the_tour(client: TestClient) -> None:
    form = {"lat": "45.764", "lon": "4.8357", "metiers": "boulangerie", "ouvert": "1"}
    response = client.post("/terrain", data=form, headers=ORIGIN, follow_redirects=False)
    assert response.headers["location"].endswith("?ouvert=1")


def test_C113_every_error_is_shown(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: object) -> int:
        raise InvalidRequest({"name": "Nom trop long : raccourcissez-le."})

    monkeypatch.setattr(routes_field, "start_field", refuse)
    form = {"lat": "45.764", "lon": "4.8357", "metiers": "boulangerie"}
    page = client.post("/terrain", data=form, headers=ORIGIN)
    assert page.status_code == 400 and "Nom trop long" in text(page)


def test_C114_tour_page_only_for_field_searches(client: TestClient, campaign_db: Engine) -> None:
    from prospection.application.campaigns import create_campaign
    from tests.application.campaign_helpers import NOW, request

    campaign_id = create_campaign(campaign_db, request(), NOW)
    assert client.get(f"/terrain/{campaign_id}").status_code == 404
