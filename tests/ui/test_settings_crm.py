"""C05 : je choisis mon CRM ; C06 : la base Notion ; C09 : sans CRM l'app marche."""

import html
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.application.api_keys import store_key
from prospection.config import Settings
from prospection.domain.services import Service
from prospection.ui.app import create_app
from prospection.ui.deps import get_http_client, get_now
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.fake_http import Handler, fake_client, json_reply

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
ORIGIN = {"Origin": "https://testserver"}
DATABASES = {
    "results": [
        {
            "object": "database",
            "id": "aaaaaaaa-0000-0000-0000-000000000001",
            "title": [{"plain_text": "Clients"}],
        },
        {
            "object": "database",
            "id": "aaaaaaaa-0000-0000-0000-000000000002",
            "title": [{"plain_text": "Prospects v2"}],
        },
    ]
}


@pytest.fixture
def make_client(settings: Settings, engine: Engine) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def build(handler: Handler, with_token: bool = True) -> TestClient:
        app = create_app(settings, engine)
        app.dependency_overrides[get_now] = lambda: NOW
        http, _ = fake_client(handler)
        app.dependency_overrides[get_http_client] = lambda: http
        if with_token:
            store_key(engine, app.state.box, Service.NOTION, "ntn_jeton", NOW)
        client = TestClient(app, base_url="https://testserver")
        client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        clients.append(client)
        return client

    yield build
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")
        conn.exec_driver_sql(
            "UPDATE app_settings SET crm='none', notion_database_id=NULL, "
            "notion_database_title=NULL"
        )


def test_C05_C06_databases_listed_and_prospects_v2_preselected(
    make_client: Callable[..., TestClient],
) -> None:
    page = html.unescape(make_client(json_reply(200, DATABASES)).get("/reglages/crm").text)
    assert "Aucun (export fichier seulement)" in page
    assert (
        '<option value="aaaaaaaa-0000-0000-0000-000000000002" selected>Prospects v2</option>'
        in page
    )
    assert '<option value="aaaaaaaa-0000-0000-0000-000000000001">Clients</option>' in page


def test_C06_choice_is_saved(make_client: Callable[..., TestClient]) -> None:
    client = make_client(json_reply(200, DATABASES))
    response = client.post(
        "/reglages/crm",
        data={"crm": "notion", "base": "aaaaaaaa-0000-0000-0000-000000000001"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = html.unescape(client.get("/reglages/crm").text)
    assert '<option value="aaaaaaaa-0000-0000-0000-000000000001" selected>Clients</option>' in page
    assert "Base actuelle : Clients" in page


def test_C06_no_database_explains_sharing(make_client: Callable[..., TestClient]) -> None:
    page = html.unescape(make_client(json_reply(200, {"results": []})).get("/reglages/crm").text)
    assert "Aucune base visible : dans Notion, ouvrez « Prospects v2 »" in page


def test_C06_notion_without_token_explains(make_client: Callable[..., TestClient]) -> None:
    page = html.unescape(
        make_client(json_reply(200, DATABASES), with_token=False).get("/reglages/crm").text
    )
    assert "Enregistrez d'abord votre jeton Notion dans Clés API." in page


def test_C06_notion_without_database_refused(make_client: Callable[..., TestClient]) -> None:
    client = make_client(json_reply(200, DATABASES))
    response = client.post("/reglages/crm", data={"crm": "notion", "base": ""}, headers=ORIGIN)
    assert response.status_code == 400
    assert "Choisissez la base Notion de destination." in html.unescape(response.text)


def test_C06_unknown_database_refused(make_client: Callable[..., TestClient]) -> None:
    client = make_client(json_reply(200, DATABASES))
    response = client.post(
        "/reglages/crm", data={"crm": "notion", "base": "inventee"}, headers=ORIGIN
    )
    assert response.status_code == 400


def test_C09_none_is_saved_and_pages_still_work(make_client: Callable[..., TestClient]) -> None:
    client = make_client(json_reply(200, DATABASES), with_token=False)
    response = client.post(
        "/reglages/crm", data={"crm": "none"}, headers=ORIGIN, follow_redirects=False
    )
    assert response.status_code == 303
    page = html.unescape(client.get("/reglages/crm").text)
    assert 'value="none" checked' in page
    for path in ["/", "/prospects", "/recherche"]:
        assert client.get(path).status_code == 200


def test_C06_notion_down_is_explained(make_client: Callable[..., TestClient]) -> None:
    page = html.unescape(make_client(json_reply(500, {})).get("/reglages/crm").text)
    assert "Réponse inattendue de Notion. Réessayez plus tard." in page
