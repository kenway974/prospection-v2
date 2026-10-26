"""C34, C35, C37, C119 : suivi en direct d'une campagne."""

import html
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from prospection.application.campaigns import create_campaign
from prospection.config import Settings
from prospection.ui.app import create_app
from prospection.ui.deps import get_now
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.application.campaign_helpers import NOW, request

ORIGIN = {"Origin": "https://testserver"}


@pytest.fixture
def client(settings: Settings, campaign_db: Engine) -> Iterator[TestClient]:
    app = create_app(settings, campaign_db)
    app.dependency_overrides[get_now] = lambda: NOW
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        yield test_client


def set_campaign(engine: Engine, campaign_id: int, **values: object) -> None:
    columns = ", ".join(f"{k} = :{k}" for k in values)
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE campaigns SET {columns} WHERE id = :id"),  # noqa: S608
                     {**values, "id": campaign_id})  # fmt: skip


def test_C34_progress_fragment_shows_counts(client: TestClient, campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(target=20), NOW)
    set_campaign(campaign_db, campaign_id, status="running", found=96, excluded=71, qualified=14)
    page = html.unescape(client.get(f"/campagnes/{campaign_id}").text)
    assert "14 sur 20 qualifiés" in page
    assert "96 trouvés" in page and "71 exclus" in page and "0 € dépensés" in page
    assert f'hx-get="/campagnes/{campaign_id}/progression"' in page
    assert 'hx-trigger="every 3s"' in page
    fragment = client.get(f"/campagnes/{campaign_id}/progression").text
    assert "<html" not in fragment and "14 sur 20 qualifiés" in fragment
    assert "En cours : cuisiniste Lyon · page 1" in html.unescape(fragment)


def test_polling_stops_when_done(client: TestClient, campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    set_campaign(
        campaign_db,
        campaign_id,
        status="done",
        stop_reason="Objectif atteint : 3 prospects qualifiés.",
    )
    page = html.unescape(client.get(f"/campagnes/{campaign_id}").text)
    assert "every 3s" not in page
    assert "Objectif atteint : 3 prospects qualifiés." in page


def test_C35_stop_button(client: TestClient, campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    set_campaign(campaign_db, campaign_id, status="running", qualified=2)
    assert "Arrêter (on garde les 2)" in html.unescape(client.get(f"/campagnes/{campaign_id}").text)
    response = client.post(
        f"/campagnes/{campaign_id}/arreter", headers=ORIGIN, follow_redirects=False
    )
    assert response.status_code == 303
    assert "Arrêt en cours" in html.unescape(client.get(f"/campagnes/{campaign_id}").text)


def test_C119_call_ready_link(client: TestClient, campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    set_campaign(campaign_db, campaign_id, status="running", qualified=4)
    page = html.unescape(client.get(f"/campagnes/{campaign_id}").text)
    assert f'href="/prospects?campagne={campaign_id}"' in page
    assert "Appeler les 4 déjà prêts" in page


def test_unknown_campaign_is_404(client: TestClient) -> None:
    assert client.get("/campagnes/999").status_code == 404


def test_campaign_list_on_search_screen(client: TestClient, campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    page = html.unescape(client.get("/recherche").text)
    assert f'href="/campagnes/{campaign_id}"' in page and "Test" in page
