"""C07 : plafond Google mensuel, 0 € par défaut ; C08 : clé Google manquante signalée."""

import html
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.application.api_keys import store_key
from prospection.config import Settings
from prospection.domain.services import Service
from prospection.ui.app import create_app
from prospection.ui.deps import get_now
from prospection.ui.session import COOKIE_NAME, make_session_value

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
ORIGIN = {"Origin": "https://testserver"}


@pytest.fixture
def client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    app = create_app(settings, engine)
    app.dependency_overrides[get_now] = lambda: NOW
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        yield test_client
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")
        conn.exec_driver_sql("UPDATE app_settings SET google_budget_cents = NULL")


def text_of(client: TestClient, path: str) -> str:
    return html.unescape(client.get(path).text)


def test_C07_default_is_zero_meaning_free_quota_only(client: TestClient) -> None:
    page = text_of(client, "/reglages/budget")
    assert "Plafond actuel : 0 € par mois" in page
    assert "l'app reste dans le quota gratuit de Google" in page


def test_C07_ceiling_saved_and_displayed(client: TestClient) -> None:
    response = client.post(
        "/reglages/budget", data={"montant": "12,50"}, headers=ORIGIN, follow_redirects=False
    )
    assert response.status_code == 303
    page = text_of(client, "/reglages/budget")
    assert "Plafond actuel : 12,50 € par mois" in page
    assert "au-delà du quota gratuit de Google" in page


def test_C07_invalid_ceiling_message(client: TestClient) -> None:
    response = client.post("/reglages/budget", data={"montant": "100"}, headers=ORIGIN)
    assert response.status_code == 400
    assert "Le plafond est limité à 50 € par mois." in html.unescape(response.text)


def test_C08_search_screen_says_google_key_missing(client: TestClient) -> None:
    page = text_of(client, "/recherche")
    assert "Ajoutez votre clé Google dans Réglages pour chercher sur Google Maps." in page
    assert "Les entreprises récemment créées restent disponibles." in page
    assert 'href="/reglages/cles"' in page
    assert "budget" not in page.lower()


def test_C08_message_disappears_when_key_saved(client: TestClient, engine: Engine) -> None:
    store_key(engine, client.app.state.box, Service.GOOGLE, "AIza-x", NOW)  # type: ignore[attr-defined]
    assert "Ajoutez votre clé Google" not in text_of(client, "/recherche")


def test_C08_unreadable_google_key_still_reported_missing(
    client: TestClient, engine: Engine
) -> None:
    from cryptography.fernet import Fernet

    from prospection.storage.secret_box import SecretBox

    store_key(engine, SecretBox(Fernet.generate_key().decode()), Service.GOOGLE, "AIza-x", NOW)
    assert "Ajoutez votre clé Google" in text_of(client, "/recherche")
