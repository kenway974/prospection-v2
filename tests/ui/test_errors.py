"""Les erreurs s'affichent en français, sans trace technique."""

import html

from fastapi.testclient import TestClient
from pydantic import SecretStr

from prospection.config import Settings
from prospection.storage.db import make_engine
from prospection.ui.app import create_app


def test_database_down_shows_french_message(settings: Settings) -> None:
    down = make_engine("postgresql+psycopg://postgres:postgres@127.0.0.1:1/x")
    app = create_app(settings, down)
    with TestClient(app, base_url="https://testserver") as client:
        response = client.post(
            "/connexion",
            data={"mot_de_passe": "x", "suite": "/"},
            headers={"Origin": "https://testserver"},
        )
    assert response.status_code == 503
    assert "La base de données ne répond pas. Réessayez dans un instant." in response.text
    assert "Traceback" not in response.text


def test_unexpected_error_shows_french_message(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"session_secret": SecretStr("t" * 32)}), None)  # type: ignore[arg-type]

    def boom() -> None:
        raise RuntimeError("détail interne")

    app.add_api_route("/boom", boom)
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        response = client.get("/boom")
    assert response.status_code == 500
    assert "Un problème est survenu." in response.text
    assert "détail interne" not in response.text
    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert response.headers["x-content-type-options"] == "nosniff"


def test_unknown_page_shows_french_message(client: TestClient) -> None:
    response = client.get("/adresse-mal-tapee")
    assert response.status_code == 404
    assert "Page introuvable. Revenez à l'accueil." in html.unescape(response.text)
    assert response.headers["content-type"].startswith("text/html")


def test_wrong_method_shows_french_message(client: TestClient) -> None:
    response = client.post("/sante", headers={"Origin": "https://testserver"})
    assert response.status_code == 405
    assert "Action impossible sur cette page. Revenez à l'accueil." in html.unescape(response.text)
