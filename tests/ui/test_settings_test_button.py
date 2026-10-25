"""C03 : bouton « Tester » ; C04 : le résultat ne montre jamais la clé."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.ui.app import create_app
from prospection.ui.deps import get_http_client, get_now
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.fake_http import fake_client, json_reply

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
HEADERS = {"Origin": "https://testserver", "HX-Request": "true"}
SECRET = "AIzaSyA-tres-secret-1234567890"


@pytest.fixture
def client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    app = create_app(settings, engine)
    app.dependency_overrides[get_now] = lambda: NOW
    http, _ = fake_client(json_reply(200, {"places": []}))
    app.dependency_overrides[get_http_client] = lambda: http
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        yield test_client
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")


def test_C03_test_button_shows_result_in_the_key_block(client: TestClient) -> None:
    client.post("/reglages/cles/google", data={"cle": SECRET}, headers=HEADERS)
    page = client.get("/reglages/cles").text
    assert 'hx-post="/reglages/cles/google/tester"' in page
    assert 'hx-target="#cle-google"' in page
    fragment = client.post("/reglages/cles/google/tester", headers=HEADERS)
    assert fragment.status_code == 200
    assert fragment.text.lstrip().startswith('<section class="group key-card" id="cle-google"')
    assert 'role="status">Clé Google valide.</p>' in fragment.text
    assert "<html" not in fragment.text


def test_C03_result_is_kept_on_the_page(client: TestClient) -> None:
    client.post("/reglages/cles/google", data={"cle": SECRET}, headers=HEADERS)
    client.post("/reglages/cles/google/tester", headers=HEADERS)
    assert "Clé Google valide." in client.get("/reglages/cles").text


def test_C03_without_htmx_the_test_redirects(client: TestClient) -> None:
    client.post("/reglages/cles/google", data={"cle": SECRET}, headers=HEADERS)
    response = client.post(
        "/reglages/cles/google/tester",
        headers={"Origin": "https://testserver"},
        follow_redirects=False,
    )
    assert (response.status_code, response.headers["location"]) == (303, "/reglages/cles")


def test_C04_test_result_never_contains_key(client: TestClient) -> None:
    client.post("/reglages/cles/google", data={"cle": SECRET}, headers=HEADERS)
    assert SECRET not in client.post("/reglages/cles/google/tester", headers=HEADERS).text
