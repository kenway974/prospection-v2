"""C11, C24 à C27, C44, C93 : campagne « entreprises récemment créées »."""

import json

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import store_key
from prospection.application.campaign_step import run_step
from prospection.application.campaigns import create_campaign, progress
from prospection.application.prospect_card import card, prospect_list
from prospection.domain.campaign_request import CampaignRequest, DepartmentZone
from prospection.domain.criteria import Criteria
from prospection.domain.services import Service
from prospection.storage.google_usage import month_usage
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place
from tests.application.test_call_tracking import PARIS
from tests.fake_http import Recorder, fake_client
from tests.sources.test_sirene_search import etab

RHONE = DepartmentZone("69", "Rhône")


def registry_request(target: int = 5, phone: str = "any", **criteria: object) -> CampaignRequest:
    return CampaignRequest(
        "Créations Rhône", ("cuisiniste",), (RHONE,), target,
        Criteria(phone=phone, **criteria), False, ("registre",),  # type: ignore[arg-type]
    )  # fmt: skip


def fake_services(
    companies: list[dict[str, object]], places: dict[str, list[dict[str, object]]]
) -> tuple[httpx.Client, Recorder]:
    """Sirene renvoie les entreprises ; Google renvoie, pour chaque nom cherché, ses fiches."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.insee.fr":
            return httpx.Response(200, json={"header": {"total": len(companies)},
                                             "etablissements": companies})  # fmt: skip
        query = json.loads(request.content)["textQuery"]
        return httpx.Response(200, json={"places": places.get(query, [])})

    return fake_client(handler)


def run_all(engine: Engine, campaign_id: int, client: httpx.Client) -> None:
    for _ in range(20):
        if run_step(engine, BOX, client, PRICING, campaign_id, NOW).done:
            return
    raise AssertionError("la campagne ne s'arrête pas")


def with_insee_key(engine: Engine) -> None:
    store_key(engine, BOX, Service.INSEE, "cle-insee", NOW)


def test_C24_C44_recent_company_found_on_google_with_its_phone(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    on_maps = {
        **api_place(1, name="Atelier Bois"), "formattedAddress": "3 rue Paul Bert, 69003 Lyon",
        "nationalPhoneNumber": "06 12 34 56 78",
    }  # fmt: skip
    client, recorder = fake_services([etab()], {"ATELIER BOIS LYON": [on_maps]})
    campaign_id = create_campaign(campaign_db, registry_request(), NOW)
    run_all(campaign_db, campaign_id, client)
    sirene = next(r for r in recorder.requests if r.url.host == "api.insee.fr")
    assert "dateCreationEtablissement:[2026-07-27 TO 2026-10-25]" in sirene.url.params["q"]
    assert "43.32*" in sirene.url.params["q"]
    [row] = prospect_list(campaign_db, None, "", "trouves").rows
    shown = card(campaign_db, row.id, NOW, PARIS)
    assert shown.tel == "0612345678" and ("Création", "14/09/2026") in shown.company_lines
    with campaign_db.connect() as conn:
        assert month_usage(conn, "2026-10")[0] == 1  # une recherche Google, comptée


def test_C24_not_on_google_kept_with_number_to_find(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    client, _ = fake_services([etab()], {})
    campaign_id = create_campaign(campaign_db, registry_request(), NOW)
    run_all(campaign_db, campaign_id, client)
    [row] = prospect_list(campaign_db, None, "", "trouves").rows
    assert "Pas trouvée sur Google Maps : numéro à chercher" in row.to_check
    assert progress(campaign_db, campaign_id).qualified == 1


def test_C26_workforce_above_the_limit_left_out(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    big = etab(siren="111111111", trancheEffectifsEtablissement="12")
    client, _ = fake_services([etab(), big], {})
    request = registry_request(max_workforce="03")
    campaign_id = create_campaign(campaign_db, request, NOW)
    run_all(campaign_db, campaign_id, client)
    assert [r.data["name"] for r in prospect_list(campaign_db, None, "", "trouves").rows] == [
        "ATELIER BOIS"
    ]


def test_C24_missing_insee_key_stops_with_reason(campaign_db: Engine) -> None:
    client, recorder = fake_services([etab()], {})
    campaign_id = create_campaign(campaign_db, registry_request(), NOW)
    run_all(campaign_db, campaign_id, client)
    assert recorder.requests == []
    assert progress(campaign_db, campaign_id).stop_reason == (
        "Clé Sirène absente : ajoutez-la dans Réglages → Clés API, ou choisissez la source "
        "Google Maps."
    )


def test_C11_both_sources_make_both_kinds_of_steps(campaign_db: Engine) -> None:
    request = CampaignRequest(
        "Les deux", ("cuisiniste",), (RHONE,), 5, Criteria(), False, ("google", "registre")
    )
    campaign_id = create_campaign(campaign_db, request, NOW)
    with campaign_db.connect() as conn:
        kinds = (
            conn.exec_driver_sql(
                "SELECT kind FROM campaign_steps WHERE campaign_id = %s ORDER BY position",
                (campaign_id,),
            )
            .scalars()
            .all()
        )
    assert kinds == ["registre", "google"]
