"""C117 : navigation flottante ; C83 : journal des connexions ; coquille mobile."""

import re
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.storage.login_journal import record_attempt
from prospection.ui.app import create_app
from prospection.ui.deps import get_now
from prospection.ui.session import COOKIE_NAME, make_session_value

NOW = datetime(2026, 10, 24, 21, 30, tzinfo=UTC)
TABS = [
    ("Aujourd'hui", "/"),
    ("Prospects", "/prospects"),
    ("Terrain", "/terrain"),
    ("Recherche", "/recherche"),
]
PAGES = [path for _, path in TABS] + ["/reglages/connexions"]


@pytest.fixture
def client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    app = create_app(settings, engine)
    app.dependency_overrides[get_now] = lambda: NOW
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        yield test_client
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM login_attempts")


def nav_of(page: str) -> str:
    match = re.search(r'<nav aria-label="Navigation principale".*?</nav>', page, re.S)
    assert match, "barre de navigation absente"
    return match.group(0)


@pytest.mark.parametrize("path", PAGES)
def test_C117_nav_on_every_page_with_four_tabs_in_order(client: TestClient, path: str) -> None:
    nav = nav_of(client.get(path).text)
    links = re.findall(r'<a href="([^"]+)"[^>]*>.*?<span>([^<]+)</span></a>', nav, re.S)
    assert [(label.replace("&#39;", "'"), href) for href, label in links] == TABS


@pytest.mark.parametrize(("label", "path"), TABS)
def test_C117_current_tab_is_marked(client: TestClient, label: str, path: str) -> None:
    nav = nav_of(client.get(path).text)
    assert nav.count('aria-current="page"') == 1
    assert re.search(rf'<a href="{re.escape(path)}" aria-current="page"', nav)


@pytest.mark.parametrize("path", PAGES)
def test_no_inline_script_or_style(client: TestClient, path: str) -> None:
    page = client.get(path).text
    assert not re.search(r"<script(?![^>]*\bsrc=)", page)
    assert not re.search(r"\sstyle=", page)
    assert not re.search(r"\son[a-z]+=", page)


def test_today_shows_local_date(client: TestClient) -> None:
    assert "dimanche 25 octobre" in client.get("/").text


def test_today_empty_state_says_what_to_do(client: TestClient) -> None:
    page = client.get("/").text.replace("&#39;", "'")
    assert "Rien de prévu. Lancez une recherche pour trouver vos premiers prospects." in page
    assert 'href="/recherche"' in page
    assert 'aria-label="Réglages"' in page


def test_C83_connection_journal_lists_date_ip_result(client: TestClient, engine: Engine) -> None:
    with engine.begin() as conn:
        record_attempt(conn, datetime(2026, 10, 24, 8, 0, tzinfo=UTC), "1.2.3.4", True)
        record_attempt(conn, datetime(2026, 10, 24, 9, 0, tzinfo=UTC), "5.6.7.8", False)
    page = client.get("/reglages/connexions").text
    assert re.search(r"24/10/2026 13:00.*5\.6\.7\.8.*Refusée", page, re.S)
    assert re.search(r"24/10/2026 12:00.*1\.2\.3\.4.*Réussie", page, re.S)
    assert "Se déconnecter" in page


def test_assets_are_linked(client: TestClient) -> None:
    page = client.get("/").text
    assert '<link rel="stylesheet" href="/static/app.css">' in page
    assert '<script src="/static/htmx-2.0.11.min.js" defer></script>' in page
    assert '<meta name="htmx-config" content=\'{"includeIndicatorStyles": false}\'>' in page
    assert client.get("/static/htmx-2.0.11.min.js").status_code == 200
