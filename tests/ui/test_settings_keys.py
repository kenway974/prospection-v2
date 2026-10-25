"""C02 : je saisis mes clés une fois ; C04 : elles ne s'affichent plus jamais en clair."""

import html
import logging
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.ui.app import create_app
from prospection.ui.deps import get_now
from prospection.ui.session import COOKIE_NAME, make_session_value

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
ORIGIN = {"Origin": "https://testserver"}
SECRET = "AIzaSyA-tres-secret-1234567890"


@pytest.fixture
def client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    app = create_app(settings, engine)
    app.dependency_overrides[get_now] = lambda: NOW
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        yield test_client
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")


def save(client: TestClient, service: str, value: str) -> httpx.Response:
    response: httpx.Response = client.post(
        f"/reglages/cles/{service}", data={"cle": value}, headers=ORIGIN, follow_redirects=False
    )
    return response


def test_settings_hub_lists_sections(client: TestClient) -> None:
    page = html.unescape(client.get("/reglages").text)
    for label in ["Clés API", "CRM", "Budget Google", "Connexions"]:
        assert label in page
    assert 'href="/reglages"' in html.unescape(client.get("/").text)


def test_C02_key_is_saved_once_and_status_shown(client: TestClient) -> None:
    response = save(client, "google", SECRET)
    assert response.status_code == 303
    page = client.get("/reglages/cles").text
    assert "Enregistrée le 25/10/2026" in page
    assert "Pas encore saisie" in page
    assert SECRET not in page
    assert 'type="password"' in page and 'autocomplete="one-time-code"' in page


def test_C04_key_never_in_page_logs_or_redirect(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    response = save(client, "google", SECRET)
    assert SECRET not in response.headers.get("location", "")
    assert SECRET not in response.text
    assert SECRET not in client.get("/reglages/cles").text
    assert SECRET not in caplog.text


def test_C02_empty_key_is_refused(client: TestClient) -> None:
    response = save(client, "notion", "   ")
    assert response.status_code == 400
    assert "Collez la clé avant d'enregistrer." in html.unescape(response.text)


def test_remove_key(client: TestClient) -> None:
    save(client, "insee", "cle-insee")
    client.post("/reglages/cles/insee/supprimer", headers=ORIGIN)
    page = client.get("/reglages/cles").text
    assert page.count("Pas encore saisie") == 3


def test_unknown_service_is_404(client: TestClient) -> None:
    assert save(client, "facebook", "x").status_code == 404
