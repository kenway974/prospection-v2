"""C24 à C27, C37, C40 : quelles entreprises du registre coûtent une recherche Google."""

import json

import httpx
from sqlalchemy import Engine, text

from prospection.application.campaigns import create_campaign, progress
from prospection.application.prospect_card import prospect_list
from prospection.domain.campaign_request import CampaignRequest
from prospection.domain.criteria import Criteria
from tests.application.campaign_helpers import NOW
from tests.application.test_registry_campaign import RHONE, run_all, with_insee_key
from tests.fake_http import fake_client
from tests.sources.test_sirene_search import etab


def default_request(target: int = 5, **criteria: object) -> CampaignRequest:
    """Réglages du formulaire par défaut : téléphone obligatoire."""
    return CampaignRequest("Créations", ("cuisiniste",), (RHONE,), target,
                           Criteria(**criteria), False, ("registre",))  # type: ignore[arg-type]  # fmt: skip


def services(companies: list[dict[str, object]], seen: list[str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.insee.fr":
            return httpx.Response(200, json={"header": {}, "etablissements": companies})
        seen.append(json.loads(request.content)["textQuery"])
        return httpx.Response(200, json={"places": []})

    return fake_client(handler)[0]


def names(engine: Engine) -> list[str]:
    return [r.data["name"] for r in prospect_list(engine, None, "", "trouves").rows]


def test_C24_not_on_maps_kept_with_default_settings(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    campaign_id = create_campaign(campaign_db, default_request(), NOW)
    run_all(campaign_db, campaign_id, services([etab()], []))
    assert names(campaign_db) == ["ATELIER BOIS"]
    assert progress(campaign_db, campaign_id).qualified == 1


def test_C24_C27_closed_old_or_other_trade_never_looked_up(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    closed = etab(siren="100000001", periodesEtablissement=[
        {"dateFin": None, "etatAdministratifEtablissement": "F",
         "activitePrincipaleEtablissement": "43.32A"}])  # fmt: skip
    old_legal = {"denominationUniteLegale": "VIEILLE SARL", "dateCreationUniteLegale": "2010-01-01"}
    old = etab(siren="100000002", uniteLegale=old_legal)
    other = etab(siren="100000003", periodesEtablissement=[
        {"dateFin": None, "etatAdministratifEtablissement": "A",
         "activitePrincipaleEtablissement": "56.10A"}])  # fmt: skip
    seen: list[str] = []
    campaign_id = create_campaign(campaign_db, default_request(), NOW)
    run_all(campaign_db, campaign_id, services([closed, old, other], seen))
    assert seen == [] and names(campaign_db) == []


def test_C24_individual_entrepreneur_searched_by_shop_sign_never_by_name(
    campaign_db: Engine,
) -> None:
    with_insee_key(campaign_db)
    person = {"nomUniteLegale": "DUPONT", "prenom1UniteLegale": "JEAN",
              "categorieJuridiqueUniteLegale": "1000"}  # fmt: skip
    signed = etab(siren="200000001", uniteLegale=person)
    unsigned = etab(siren="200000002", uniteLegale=person, periodesEtablissement=[
        {"dateFin": None, "etatAdministratifEtablissement": "A",
         "activitePrincipaleEtablissement": "43.32A"}])  # fmt: skip
    seen: list[str] = []
    campaign_id = create_campaign(campaign_db, default_request(), NOW)
    run_all(campaign_db, campaign_id, services([signed, unsigned], seen))
    assert seen == ["BOIS & CO LYON"]  # l'enseigne ; jamais le nom d'une personne


def test_C40_same_company_twice_in_a_page_paid_once(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    seen: list[str] = []
    campaign_id = create_campaign(campaign_db, default_request(min_reviews=3), NOW)
    run_all(campaign_db, campaign_id, services([etab(), etab(siret="92345678900099")], seen))
    assert len(seen) == 1


def test_C16_google_lookups_capped_per_campaign(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    many = [etab(siren=f"30000000{n}") for n in range(8)]
    seen: list[str] = []
    request = default_request(target=1, min_reviews=3)  # aucune ne sera qualifiée
    campaign_id = create_campaign(campaign_db, request, NOW)
    run_all(campaign_db, campaign_id, services(many, seen))
    assert len(seen) == 5  # 5 recherches au plus par prospect voulu


def test_C35_stop_request_honoured_inside_a_page(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    many = [etab(siren=f"40000000{n}") for n in range(5)]
    seen: list[str] = []
    campaign_id = create_campaign(campaign_db, default_request(min_reviews=3), NOW)
    client = services(many, seen)

    def stop_after_first(request: httpx.Request) -> None:
        if len(seen) == 1:
            with campaign_db.begin() as conn:
                conn.execute(text("UPDATE campaigns SET status = 'stopping'"))

    client.event_hooks["response"] = [lambda response: stop_after_first(response.request)]
    run_all(campaign_db, campaign_id, client)
    assert len(seen) == 1


def test_C37_registry_only_campaign_ends_with_its_own_reason(campaign_db: Engine) -> None:
    with_insee_key(campaign_db)
    campaign_id = create_campaign(campaign_db, default_request(min_reviews=3), NOW)
    run_all(campaign_db, campaign_id, services([], []))
    assert progress(campaign_db, campaign_id).stop_reason == (
        "Plus d'entreprises récemment créées pour ces métiers et cette zone "
        "(0 qualifié sur 5 voulus)."
    )
