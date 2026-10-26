"""C61, C106, C107 : saisie gardée sans HTMX, enregistrement au fil de l'eau, annuler, tri."""

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from tests.ui.test_call_screens import HX, client, names, text

__all__ = ["client"]  # fixture partagée


def test_C106_without_htmx_refused_input_shows_the_whole_card(
    client: TestClient, campaign_db: Engine
) -> None:
    [pid] = names(campaign_db, "A")
    response = client.post(
        f"/prospects/{pid}/contact", data={"dirigeant": "Marie", "mobile": "12", "email": ""},
        headers={"Origin": "https://testserver"},
    )  # fmt: skip
    assert response.status_code == 422 and "<html" in response.text
    assert 'value="Marie"' in text(response) and 'aria-invalid="true"' in response.text


def test_C106_fields_save_as_soon_as_changed(client: TestClient, campaign_db: Engine) -> None:
    [pid] = names(campaign_db, "A")
    page = client.get(f"/prospects/{pid}").text
    assert page.count('hx-trigger="change, submit"') == 2  # action et contact
    script = client.get("/static/app.js").text
    assert "beforeunload" in script and "htmx:responseError" in script


def test_C107_finish_can_be_undone_and_unknown_is_not_found(
    client: TestClient, campaign_db: Engine
) -> None:
    [pid] = names(campaign_db, "A")
    action = {"type": "rappeler", "date": "2026-10-25", "heure": ""}
    client.post(f"/prospects/{pid}/action", data=action, headers=HX)
    action_id = text(client.get("/")).split('action="/actions/')[1].split("/")[0]
    origin = {"Origin": "https://testserver"}
    done = client.post(f"/actions/{action_id}/terminer", headers=origin, follow_redirects=False)
    assert done.headers["location"] == f"/?terminee={action_id}"
    assert "Action terminée." in text(client.get(done.headers["location"]))
    client.post(f"/actions/{action_id}/rouvrir", headers=origin)
    assert "Dans la journée · Rappeler" in text(client.get("/"))
    assert client.post("/actions/999/terminer", headers=origin).status_code == 404


def test_C61_sort_offered(client: TestClient, campaign_db: Engine) -> None:
    names(campaign_db, "Zola", "Alpha")
    page = text(client.get("/prospects", params={"tri": "nom"}))
    assert page.index("Alpha") < page.index("Zola")
    assert '<option value="nom" selected>Nom</option>' in page
