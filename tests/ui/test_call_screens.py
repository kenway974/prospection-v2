"""C61, C102 à C107, C109, C120 : écrans Prospects, fiche d'appel et Aujourd'hui."""

import dataclasses
import html
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.ui.app import create_app
from prospection.ui.deps import get_now
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE

HX = {"Origin": "https://testserver", "HX-Request": "true"}


@pytest.fixture
def client(settings: Settings, campaign_db: Engine) -> Iterator[TestClient]:
    app = create_app(settings, campaign_db)
    app.dependency_overrides[get_now] = lambda: NOW
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        yield test_client


def text(response: object) -> str:
    return html.unescape(response.text)  # type: ignore[attr-defined]


def names(engine: Engine, *values: str) -> list[int]:
    places = [dataclasses.replace(PLACE, place_id=f"p{n}", name=v) for n, v in enumerate(values)]
    return add(engine, *places)


def test_C120_list_searched_and_filtered_with_counts(
    client: TestClient, campaign_db: Engine
) -> None:
    first, _ = names(campaign_db, "Cuisines Martin", "<script>alert(1)</script>")
    client.post(f"/prospects/{first}/resultat", data={"statut": "intéressé"}, headers=HX)
    page = client.get("/prospects").text
    assert "&lt;script&gt;" in page and "<script>alert" not in page
    assert "À appeler · 1" in text(client.get("/prospects")) and "Intéressé · 1" in text(
        client.get("/prospects")
    )
    filtered = text(client.get("/prospects", params={"statut": "intéressé"}))
    assert "Cuisines Martin" in filtered and "alert(1)" not in filtered
    assert "Cuisines Martin" in text(client.get("/prospects", params={"q": "martin"}))
    assert 'href="/prospects/' in page and "Démarrer la session d'appel" in page
    assert (
        client.post(
            "/prospects/session", headers={"Origin": "https://ailleurs.example"}
        ).status_code
        == 403
    )


def test_C109_session_started_from_the_list_then_resumed(
    client: TestClient, campaign_db: Engine
) -> None:
    first, second, third = names(campaign_db, "Alpha", "Bravo", "Charlie")
    start = client.post(
        "/prospects/session", data={"statut": "à appeler"},
        headers={"Origin": "https://testserver"}, follow_redirects=False,
    )  # fmt: skip
    assert start.headers["location"] == f"/prospects/{first}?session=1"
    page = text(client.get(f"/prospects/{second}?session=1"))
    assert "2 / 3" in page
    assert f'href="/prospects/{first}?session=1"' in page
    assert f'href="/prospects/{third}?session=1"' in page
    assert 'href="tel:+33612345678"' in page and "Recherche Google" in page
    today = text(client.get("/"))
    assert "Reprendre la session" in today and "Bravo · 2 / 3" in today


def test_C102_C103_result_saved_in_one_gesture(client: TestClient, campaign_db: Engine) -> None:
    [pid] = names(campaign_db, "A")
    response = client.post(f"/prospects/{pid}/resultat", data={"statut": "messagerie"}, headers=HX)
    fragment = text(response)
    assert response.status_code == 200 and "<html" not in fragment
    assert 'value="messagerie" aria-pressed="true"' in fragment
    assert 'value="2026-10-26"' in fragment  # Rappeler demain, préparé (pas enregistré)
    assert "Proposée : vérifiez, puis enregistrez." in fragment


def test_C106_refused_input_says_why_and_keeps_it(client: TestClient, campaign_db: Engine) -> None:
    [pid] = names(campaign_db, "A")
    data = {"type": "rappeler", "date": "2026-10-27", "heure": "25:00"}
    response = client.post(f"/prospects/{pid}/action", data=data, headers=HX)
    assert response.status_code == 422
    assert "Heure invalide : écrivez-la ainsi, 14:30." in text(response)
    assert 'value="25:00"' in text(response)
    contact = {"dirigeant": "Marie", "mobile": "12", "email": ""}
    bad = client.post(f"/prospects/{pid}/contact", data=contact, headers=HX)
    assert bad.status_code == 422 and 'value="Marie"' in text(bad)


def test_C106_network_failure_message_ready(client: TestClient) -> None:
    page = client.get("/").text
    assert 'id="erreur-reseau"' in page and "htmx-config" in page
    assert "htmx:sendError" in client.get("/static/app.js").text


def test_C104_C105_note_and_contact_saved(client: TestClient, campaign_db: Engine) -> None:
    [pid] = names(campaign_db, "A")
    note = client.post(f"/prospects/{pid}/note", data={"texte": "Devis en cours"}, headers=HX)
    assert "Devis en cours" in text(note) and "25/10/2026" in text(note)
    contact = {"dirigeant": "Marie", "mobile": "06 12 34 56 78", "email": ""}
    saved = client.post(f"/prospects/{pid}/contact", data=contact, headers=HX)
    assert 'value="+33612345678"' in text(saved) and "Enregistré" in text(saved)


def test_C107_today_lists_and_finishes_actions(client: TestClient, campaign_db: Engine) -> None:
    [pid] = names(campaign_db, "Cuisines Martin")
    action = {"type": "rendez-vous", "date": "2026-10-25", "heure": "14:30"}
    client.post(f"/prospects/{pid}/action", data=action, headers=HX)
    page = text(client.get("/"))
    assert "Aujourd'hui" in page and "14:30" in page and "Rendez-vous" in page
    action_id = page.split('action="/actions/')[1].split("/")[0]
    done = client.post(f"/actions/{action_id}/terminer", headers={"Origin": "https://testserver"},
                       follow_redirects=False)  # fmt: skip
    assert done.status_code == 303 and "14:30" not in text(client.get("/"))


def test_without_htmx_forms_redirect_back(client: TestClient, campaign_db: Engine) -> None:
    [pid] = names(campaign_db, "A")
    origin = {"Origin": "https://testserver"}
    response = client.post(
        f"/prospects/{pid}/resultat",
        data={"statut": "intéressé"},
        headers=origin,
        follow_redirects=False,
    )
    assert (response.status_code, response.headers["location"]) == (303, f"/prospects/{pid}")


def test_unknown_prospect_is_not_found(client: TestClient) -> None:
    assert client.get("/prospects/999").status_code == 404
