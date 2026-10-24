"""C01 : accès protégé ; C82 : limite d'essais ; C116 : session de 30 jours."""

import html
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.ui.app import create_app
from prospection.ui.deps import get_now
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.ui.conftest import PASSWORD

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=UTC)
ORIGIN = {"Origin": "https://testserver"}


@pytest.fixture
def clock() -> list[datetime]:
    return [NOW]


@pytest.fixture
def client(settings: Settings, engine: Engine, clock: list[datetime]) -> Iterator[TestClient]:
    app = create_app(settings, engine)
    app.dependency_overrides[get_now] = lambda: clock[0]
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM login_attempts")


def login(client: TestClient, password: str = PASSWORD, suite: str = "/") -> httpx.Response:
    response: httpx.Response = client.post(
        "/connexion",
        data={"mot_de_passe": password, "suite": suite},
        headers=ORIGIN,
        follow_redirects=False,
    )
    return response


def test_C01_pages_require_login(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/connexion?suite=/"


def test_C01_login_form_is_labelled(client: TestClient) -> None:
    page = client.get("/connexion").text
    assert '<label for="mot_de_passe">Mot de passe</label>' in page
    assert "Se connecter" in page


def test_C01_login_then_access(client: TestClient) -> None:
    response = login(client)
    assert (response.status_code, response.headers["location"]) == (303, "/")
    cookie = response.headers["set-cookie"]
    for part in ["Max-Age=2592000", "HttpOnly", "Secure", "SameSite=lax", "Path=/"]:
        assert part in cookie
    assert client.get("/", follow_redirects=False).status_code == 200


def test_C01_wrong_password_message(client: TestClient) -> None:
    response = login(client, "faux")
    assert response.status_code == 401
    assert "Mot de passe incorrect." in response.text


def test_C82_lock_message_says_when_to_retry(client: TestClient) -> None:
    for _ in range(5):
        login(client, "faux")
    response = login(client)
    assert response.status_code == 429
    assert "Trop d'essais. Réessayez dans 15 min." in html.unescape(response.text)


def test_C116_session_lasts_30_days_and_slides(
    client: TestClient, settings: Settings, clock: list[datetime]
) -> None:
    client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW - timedelta(days=29)))
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert COOKIE_NAME in response.headers["set-cookie"]
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW - timedelta(days=31)))
    assert client.get("/", follow_redirects=False).status_code == 303


def test_C116_fresh_session_is_not_reissued(client: TestClient, settings: Settings) -> None:
    client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW - timedelta(hours=1)))
    response = client.get("/", follow_redirects=False)
    assert "set-cookie" not in response.headers


def test_session_invalid_after_password_change(client: TestClient, settings: Settings) -> None:
    other = settings.model_copy(update={"app_password_hash": SecretStr("$argon2id$autre")})
    client.cookies.set(COOKIE_NAME, make_session_value(other, NOW))
    assert client.get("/", follow_redirects=False).status_code == 303


def test_tampered_cookie_redirects(client: TestClient) -> None:
    client.cookies.set(COOKIE_NAME, "n'importe.quoi")
    assert client.get("/", follow_redirects=False).status_code == 303


@pytest.mark.parametrize("suite", ["//evil.example", "https://evil.example", "/\\evil.example"])
def test_open_redirect_is_blocked(client: TestClient, suite: str) -> None:
    assert login(client, suite=suite).headers["location"] == "/"


def test_login_keeps_relative_destination(client: TestClient) -> None:
    assert login(client, suite="/prospects").headers["location"] == "/prospects"


def test_logout_clears_session(client: TestClient) -> None:
    login(client)
    response = client.post("/deconnexion", headers=ORIGIN, follow_redirects=False)
    assert response.headers["location"] == "/connexion"
    assert client.get("/", follow_redirects=False).status_code == 303


def test_cookie_uses_host_prefix() -> None:
    assert COOKIE_NAME == "__Host-session"
