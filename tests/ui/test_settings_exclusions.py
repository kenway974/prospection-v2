"""C30 : ma liste de franchises ; C33 : ma liste noire."""

import html
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.ui.app import create_app
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.application.campaign_helpers import NOW

ORIGIN = {"Origin": "https://testserver"}


@pytest.fixture
def client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    with TestClient(create_app(settings, engine), base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        yield test_client
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM exclusion_names")


def test_C30_C33_lists_saved_and_shown(client: TestClient) -> None:
    response = client.post(
        "/reglages/exclusions",
        data={"franchises": "Mon Enseigne\n\nAutre Chaîne", "liste_noire": "Cuisines Lefèvre"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = html.unescape(client.get("/reglages/exclusions").text)
    assert "Autre Chaîne\nMon Enseigne</textarea>" in page
    assert "Cuisines Lefèvre</textarea>" in page
    assert '<label for="liste_noire">Liste noire (un nom par ligne)</label>' in page


def test_settings_hub_links_exclusions(client: TestClient) -> None:
    assert 'href="/reglages/exclusions"' in client.get("/reglages").text


def test_C30_too_many_names_refused_without_change(client: TestClient) -> None:
    names = "\n".join(f"Nom {i}" for i in range(501))
    response = client.post(
        "/reglages/exclusions", data={"franchises": names, "liste_noire": "X"}, headers=ORIGIN
    )
    assert response.status_code == 400
    assert "500 noms au plus" in response.text
    assert "X</textarea>" not in client.get("/reglages/exclusions").text
