"""C40, C41 : une campagne « registre » ne repaie jamais une recherche déjà faite."""

import httpx
from sqlalchemy import Engine

from prospection.application.campaigns import create_campaign
from prospection.application.prospect_card import prospect_list
from prospection.storage.google_usage import month_usage
from tests.application.campaign_helpers import NOW
from tests.application.test_registry_campaign import registry_request, run_all, with_insee_key
from tests.fake_http import fake_client
from tests.sources.test_sirene_search import etab


def test_C40_replayed_page_never_pays_twice_for_the_same_company(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    second = etab(siren="222222222", uniteLegale={"denominationUniteLegale": "BOIS DEUX"})
    calls = {"google": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.insee.fr":
            return httpx.Response(200, json={"header": {}, "etablissements": [etab(), second]})
        calls["google"] += 1
        if calls["google"] == 2:
            return httpx.Response(503, json={})  # Google trop sollicité sur la 2e entreprise
        return httpx.Response(200, json={"places": []})

    client, _ = fake_client(handler)
    campaign_id = create_campaign(campaign_db, registry_request(), NOW)
    run_all(campaign_db, campaign_id, client)
    assert calls["google"] == 2  # chaque entreprise cherchée une fois, même après le 503
    with campaign_db.connect() as conn:
        assert month_usage(conn, "2026-10")[0] == 2
    rows = prospect_list(campaign_db, None, "", "trouves").rows
    assert len(rows) == 2  # la 2e est gardée, numéro à chercher
    assert any("numéro à chercher" in " ".join(r.to_check) for r in rows)


def test_C41_google_refusing_one_company_keeps_it_to_look_up(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.insee.fr":
            return httpx.Response(200, json={"header": {}, "etablissements": [etab()]})
        return httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT"}})

    client, _ = fake_client(handler)
    campaign_id = create_campaign(campaign_db, registry_request(), NOW)
    run_all(campaign_db, campaign_id, client)
    [row] = prospect_list(campaign_db, None, "", "trouves").rows
    assert "Pas trouvée sur Google Maps : numéro à chercher" in row.to_check
