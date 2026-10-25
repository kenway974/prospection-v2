"""C10 à C18, C08 : écran Recherche."""

import html
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.application.api_keys import store_key
from prospection.config import Settings
from prospection.domain.services import Service
from prospection.ui.app import create_app
from prospection.ui.deps import get_http_client, get_now
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.fake_http import fake_client

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
ORIGIN = {"Origin": "https://testserver"}
COMMUNES = [
    {"nom": "Saint-Denis", "code": "93066", "centre": {"coordinates": [2.35, 48.93]}},
    {"nom": "Saint-Denis", "code": "97411", "centre": {"coordinates": [55.45, -20.88]}},
]
CHOSEN = "FR|97411|-20.88|55.45|Saint-Denis"
FORM = {
    "nom": "Cuisinistes Saint-Denis",
    "metiers": "cuisiniste",
    "synonymes": "on",
    "commune": CHOSEN,
    "rayon": "0",
    "departements": "",
    "nombre": "20",
    "avis_max": "30",
    "avis_min": "",
    "site": "any",
    "telephone": "with",
    "franchises": "on",
}


@pytest.fixture
def client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    app = create_app(settings, engine)
    app.dependency_overrides[get_now] = lambda: NOW
    http, _ = fake_client(lambda r: httpx.Response(200, json=COMMUNES))
    app.dependency_overrides[get_http_client] = lambda: http
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        store_key(engine, app.state.box, Service.GOOGLE, "AIza-x", NOW)
        yield test_client
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "TRUNCATE campaigns, campaign_steps, campaign_templates, api_keys "
            "RESTART IDENTITY CASCADE"
        )


def post(client: TestClient, **changes: str) -> httpx.Response:
    response: httpx.Response = client.post(
        "/recherche", data={**FORM, **changes}, headers=ORIGIN, follow_redirects=False
    )
    return response


def text(response: httpx.Response) -> str:
    return html.unescape(response.text)


def test_launch_creates_campaign_and_redirects(client: TestClient) -> None:
    response = post(client)
    assert (response.status_code, response.headers["location"]) == (303, "/campagnes/1")


def test_C17_errors_shown_per_field(client: TestClient) -> None:
    response = post(client, metiers=" ", commune="", departements="", nom="")
    assert response.status_code == 400
    page = text(response)
    assert "Indiquez au moins un métier." in page
    assert "Indiquez au moins une ville, un département ou un rayon." in page
    assert "Donnez un nom à la campagne." in page


def test_C13_ambiguous_city_asks_to_choose(client: TestClient) -> None:
    fragment = text(client.get("/recherche/communes", params={"ville": "Saint-Denis"}))
    assert "Saint-Denis (93)" in fragment and "Saint-Denis (974)" in fragment
    assert f'value="{CHOSEN}"' in fragment


def test_C13_unknown_department_refused(client: TestClient) -> None:
    response = post(client, commune="", departements="974, Atlantide")
    assert "Département inconnu : Atlantide." in text(response)


def test_C13_tampered_commune_refused(client: TestClient) -> None:
    response = post(client, commune="x|y|z")
    assert response.status_code == 400
    assert "Choisissez la commune dans la liste." in text(response)


def test_C15_synonyms_listed(client: TestClient) -> None:
    fragment = text(client.get("/recherche/synonymes", params={"metiers": "cuisiniste"}))
    assert "cuisine sur mesure" in fragment


def test_C16_estimate_shown_before_launch(client: TestClient) -> None:
    fragment = text(client.post("/recherche/estimation", data=FORM, headers=ORIGIN))
    assert "Coût estimé : 0 € (dans le quota gratuit de Google)" in fragment
    assert "9 pages au plus" in fragment


def test_C18_template_saved_and_reloaded(client: TestClient) -> None:
    post(client, modele="Cuisinistes 974")
    page = text(client.get("/recherche"))
    assert "Cuisinistes 974" in page
    page = text(client.get("/recherche", params={"modele": "Cuisinistes 974"}))
    assert 'value="Cuisinistes Saint-Denis"' in page


def test_C08_launch_refused_without_google_key(client: TestClient, engine: Engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")
    response = post(client)
    assert response.status_code == 400
    assert "Ajoutez votre clé Google dans Réglages pour chercher sur Google Maps." in text(response)


def test_search_form_is_labelled(client: TestClient) -> None:
    page = text(client.get("/recherche"))
    for label in [
        "Nom de la campagne",
        "Métiers",
        "Ville",
        "Rayon autour (km)",
        "Départements, provinces ou cantons",
        "Prospects qualifiés voulus",
        "Avis au plus",
    ]:
        assert f">{label}</label>" in page, label
