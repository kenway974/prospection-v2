"""C127 à C129 : liste des prospects par origine, par campagne, suppression groupée."""

import dataclasses

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.domain.criteria import Verdict
from prospection.domain.prospect_source import FIELD
from prospection.storage.campaigns import create_campaign
from prospection.storage.privacy import erased_keys
from prospection.storage.prospects import insert_prospect
from tests.application.campaign_helpers import NOW, request
from tests.storage.test_campaigns import PLACE, STEPS
from tests.ui.test_call_screens import client, text
from tests.ui.test_search_form import ORIGIN

__all__ = ["client"]  # fixture partagée


def _campaign(engine: Engine, name: str, *places: str, kind: str = "appel") -> int:
    with engine.begin() as conn:
        campaign_id = create_campaign(
            conn, dataclasses.replace(request(), name=name), STEPS, NOW, kind=kind
        )
        for place in places:
            row = dataclasses.replace(PLACE, place_id=place, name=place)
            insert_prospect(conn, campaign_id, row, "cuisiniste", Verdict(True, (), ()), NOW)
    return campaign_id


def test_C127_calls_and_field_listed_apart(client: TestClient, campaign_db: Engine) -> None:
    _campaign(campaign_db, "Cuisinistes Lyon", "Cuisines Martin")
    _campaign(campaign_db, "Terrain · Croix-Rousse", "Boulangerie Paul", kind=FIELD)
    calls = text(client.get("/prospects"))
    assert "Cuisines Martin" in calls and "Boulangerie Paul" not in calls
    assert "À appeler · 1" in calls and "Terrain · 1" in calls
    field = text(client.get("/prospects", params={"origine": "terrain"}))
    assert "Boulangerie Paul" in field and "Cuisines Martin" not in field
    assert 'name="origine" value="terrain"' in field  # la session d'appel garde l'origine


def test_C128_list_filtered_by_campaign(client: TestClient, campaign_db: Engine) -> None:
    lyon = _campaign(campaign_db, "Cuisinistes Lyon", "Cuisines Martin")
    _campaign(campaign_db, "Cuisinistes Paris", "Cuisines Durand")
    page = text(client.get("/prospects"))
    assert "Cuisinistes Lyon · 1" in page and "Cuisinistes Paris · 1" in page
    only = text(client.get("/prospects", params={"campagne": str(lyon)}))
    assert "Cuisines Martin" in only and "Cuisines Durand" not in only
    assert f'name="campagne" value="{lyon}"' in only
    assert "Cuisines Durand" in text(client.get("/prospects", params={"campagne": "x"}))


def test_C129_bulk_delete_after_confirmation(client: TestClient, campaign_db: Engine) -> None:
    _campaign(campaign_db, "Cuisinistes Lyon", "Cuisines Martin", "Cuisines Durand", "Atelier")
    page = text(client.get("/prospects"))
    assert page.count('type="checkbox" name="id"') == 3
    ids = [int(part.split('"')[0]) for part in page.split('name="id" value="')[1:]]
    confirm = text(client.post("/prospects/selection", data={"id": ids[:2]}, headers=ORIGIN))
    assert "Cuisines Martin" in confirm and "Cuisines Durand" in confirm
    assert "Atelier" not in confirm
    done = client.post("/prospects/selection/supprimer", data={"id": ids[:2]}, headers=ORIGIN,
                       follow_redirects=False)  # fmt: skip
    assert done.headers["location"] == "/prospects?supprime=2"
    after = text(client.get(done.headers["location"]))
    assert "2 prospects supprimés" in after and "Cuisines Martin" not in after
    assert "Atelier" in after


def test_C129_nothing_selected_goes_back(client: TestClient) -> None:
    empty = client.post("/prospects/selection", headers=ORIGIN, follow_redirects=False)
    assert empty.headers["location"] == "/prospects"
    bad = client.post("/prospects/selection/supprimer", headers=ORIGIN, follow_redirects=False)
    assert bad.headers["location"] == "/prospects"


def test_C129_never_found_again_when_asked(client: TestClient, campaign_db: Engine) -> None:
    _campaign(campaign_db, "Cuisinistes Lyon", "Cuisines Martin")
    page = text(client.get("/prospects"))
    pid = int(page.split('name="id" value="')[1].split('"')[0])
    client.post("/prospects/selection/supprimer", data={"id": [pid], "jamais": "on"},
                headers=ORIGIN)  # fmt: skip
    with campaign_db.connect() as conn:
        assert erased_keys(conn)  # empreinte : une recherche ne la reprendra plus


def test_C130_only_card_inputs_guard_against_leaving(
    client: TestClient, campaign_db: Engine
) -> None:
    _campaign(campaign_db, "Cuisinistes Lyon", "Cuisines Martin")
    page = text(client.get("/prospects"))
    pid = int(page.split('name="id" value="')[1].split('"')[0])
    assert text(client.get(f"/prospects/{pid}")).count("data-garde") == 4  # note, contact, suivi
    assert "data-garde" not in text(client.get("/recherche"))  # lancer une campagne : rien


def test_C128_campaign_of_another_tab_ignored(client: TestClient, campaign_db: Engine) -> None:
    _campaign(campaign_db, "Cuisinistes Lyon", "Cuisines Martin")
    field = _campaign(campaign_db, "Terrain · Croix-Rousse", "Boulangerie Paul", kind=FIELD)
    page = text(client.get("/prospects", params={"campagne": str(field)}))
    assert "Cuisines Martin" in page and f'value="{field}"' not in page


def test_C129_back_to_the_same_tab_and_campaign(client: TestClient, campaign_db: Engine) -> None:
    field = _campaign(campaign_db, "Terrain · Croix-Rousse", "Boulangerie Paul", kind=FIELD)
    page = text(client.get("/prospects", params={"origine": "terrain"}))
    pid = int(page.split('name="id" value="')[1].split('"')[0])
    form = {"id": [pid], "origine": "terrain", "campagne": str(field)}
    done = client.post("/prospects/selection/supprimer", data=form, headers=ORIGIN,
                       follow_redirects=False)  # fmt: skip
    assert done.headers["location"] == f"/prospects?supprime=1&origine=terrain&campagne={field}"


def test_C120_search_without_result_keeps_the_form(client: TestClient, campaign_db: Engine) -> None:
    _campaign(campaign_db, "Cuisinistes Lyon", "Cuisines Martin")
    page = text(client.get("/prospects", params={"q": "introuvable"}))
    assert "Aucun prospect ne correspond" in page and 'id="q"' in page


def test_C133_list_shows_one_block_per_campaign(client: TestClient, campaign_db: Engine) -> None:
    _campaign(campaign_db, "Cuisinistes Lyon", "Cuisines Martin")
    _campaign(campaign_db, "Cuisinistes Paris", "Cuisines Durand")
    page = text(client.get("/prospects"))
    paris, lyon = (
        page.index('<h2 class="group-title">Cuisinistes Paris · 1</h2>'),
        page.index('<h2 class="group-title">Cuisinistes Lyon · 1</h2>'),
    )
    assert paris < page.index("Cuisines Durand") < lyon < page.index("Cuisines Martin")
