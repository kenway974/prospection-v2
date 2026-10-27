"""C39, C28, C46, C47 : sites lus pendant la campagne, après les critères gratuits."""

import dataclasses

from sqlalchemy import Engine

from prospection.application.campaign_step import run_step
from prospection.application.campaigns import create_campaign, progress
from prospection.application.prospect_card import prospect_list
from prospection.domain.criteria import Criteria
from prospection.domain.place import Place
from prospection.domain.site_audit import Audit
from prospection.domain.site_report import SiteReport
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place, pages, request
from tests.fake_http import fake_client

GOOD = Audit(90, (), "WordPress", https=True, mobile=True, contact_form=True)


class FakeSites:
    """Faux lecteur de sites : rapport choisi par nom d'établissement."""

    def __init__(self, reports: dict[str, SiteReport]) -> None:
        self.reports = reports
        self.checked: list[str] = []

    def __call__(self, place: Place, keywords: tuple[str, ...]) -> SiteReport:
        self.checked.append(place.name)
        return self.reports.get(place.name, SiteReport("aucun"))


def run(engine: Engine, criteria: Criteria, places: list[dict[str, object]], sites: FakeSites,
        target: int = 5) -> int:  # fmt: skip
    client, _ = fake_client(pages(places))
    campaign_id = create_campaign(
        engine, dataclasses.replace(request(target=target), criteria=criteria), NOW
    )
    for _ in range(10):
        if run_step(engine, BOX, client, PRICING, campaign_id, NOW, sites).done:
            break
    return campaign_id


def test_C39_site_read_only_after_free_criteria(campaign_db: Engine) -> None:
    sites = FakeSites({})
    places = [api_place(1, reviews=500), api_place(2)]
    run(campaign_db, Criteria(phone="any", max_reviews=30), places, sites)
    assert sites.checked == ["Cuisines Martin 2"]  # trop d'avis : site jamais lu


def test_C28_good_site_excluded_when_only_weak_sites_wanted(campaign_db: Engine) -> None:
    good = SiteReport("fiche Google", "https://martin.fr", audit=GOOD)
    sites = FakeSites({"Cuisines Martin 1": good})
    criteria = Criteria(phone="any", max_site_score=50)
    campaign_id = run(campaign_db, criteria, [api_place(1), api_place(2)], sites)
    state = progress(campaign_db, campaign_id)
    assert (state.qualified, state.excluded) == (1, 1)
    with campaign_db.connect() as conn:
        reasons = conn.exec_driver_sql("SELECT reasons FROM prospects WHERE NOT qualified")
        assert [r for (r,) in reasons] == [["Site correct (90/100)"]]


def test_C46_found_site_satisfies_with_site(campaign_db: Engine) -> None:
    found = SiteReport("retrouvé", "https://cuisines-martin-1.fr", audit=GOOD)
    sites = FakeSites({"Cuisines Martin 1": found})
    campaign_id = run(campaign_db, Criteria(phone="any", website="with"),
                      [api_place(1), api_place(2)], sites)  # fmt: skip
    assert progress(campaign_db, campaign_id).qualified == 1
    [row] = prospect_list(campaign_db, None, "", "trouves").rows
    assert row.site is not None and row.site.url == "https://cuisines-martin-1.fr"


def test_C47_probable_site_only_to_check(campaign_db: Engine) -> None:
    probable = SiteReport("aucun", probable="https://cuisinesmartin1.fr")
    sites = FakeSites({"Cuisines Martin 1": probable})
    run(campaign_db, Criteria(phone="any"), [api_place(1)], sites)
    [row] = prospect_list(campaign_db, None, "", "trouves").rows
    assert "Site probable, à confirmer (homonyme possible)" in row.to_check


def test_C46_registry_company_site_found_and_audited(campaign_db: Engine) -> None:
    """Entreprise récemment créée, absente de Maps : son site est cherché à partir du nom."""
    from tests.application.test_registry_campaign import with_insee_key
    from tests.application.test_registry_rules import default_request, services
    from tests.sources.test_sirene_search import etab

    with_insee_key(campaign_db)
    found = SiteReport("retrouvé", "https://atelier-bois.fr", audit=GOOD)
    sites = FakeSites({"BOIS & CO": found})
    campaign_id = create_campaign(campaign_db, default_request(max_site_score=50), NOW)
    client = services([etab()], [])
    for _ in range(10):
        if run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, sites).done:
            break
    assert sites.checked == ["BOIS & CO"]
    with campaign_db.connect() as conn:
        reasons = conn.exec_driver_sql("SELECT reasons FROM prospects")
        assert [r for (r,) in reasons] == [["Site correct (90/100)"]]


def test_C52_card_shows_the_site_and_its_link(campaign_db: Engine) -> None:
    from prospection.application.prospect_card import card
    from tests.application.test_call_tracking import PARIS

    found = SiteReport("retrouvé", "https://cuisines-martin-1.fr", audit=GOOD)
    run(campaign_db, Criteria(phone="any"), [api_place(1)], FakeSites({"Cuisines Martin 1": found}))
    [row] = prospect_list(campaign_db, None, "", "trouves").rows
    shown = card(campaign_db, row.id, NOW, PARIS)
    assert ("Score", "90/100") in shown.site_lines
    assert shown.website == "https://cuisines-martin-1.fr"  # site retrouvé : bouton « Site web »


def test_C47_individual_without_sign_never_guessed(campaign_db: Engine) -> None:
    """Entrepreneur individuel sans enseigne : son nom est celui d'une personne (RGPD)."""
    from tests.application.test_registry_campaign import with_insee_key
    from tests.application.test_registry_rules import default_request, services
    from tests.sources.test_sirene_search import etab

    with_insee_key(campaign_db)
    person = etab(
        uniteLegale={"nomUniteLegale": "DUPONT", "prenom1UniteLegale": "JEAN",
                     "categorieJuridiqueUniteLegale": "1000"},
        periodesEtablissement=[{"dateFin": None, "etatAdministratifEtablissement": "A",
                                "activitePrincipaleEtablissement": "43.32A"}],
    )  # fmt: skip
    sites = FakeSites({})
    campaign_id = create_campaign(campaign_db, default_request(), NOW)
    client = services([person], [])
    for _ in range(10):
        if run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, sites).done:
            break
    assert sites.checked == []
    [row] = prospect_list(campaign_db, None, "", "trouves").rows
    assert row.site is not None and "sans enseigne" in (row.site.problem or "")


def test_C46_registry_site_guessed_from_the_shop_sign(campaign_db: Engine) -> None:
    from tests.application.test_registry_campaign import with_insee_key
    from tests.application.test_registry_rules import default_request, services
    from tests.sources.test_sirene_search import etab

    with_insee_key(campaign_db)
    sites = FakeSites({})
    campaign_id = create_campaign(campaign_db, default_request(), NOW)
    client = services([etab()], [])
    for _ in range(10):
        if run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, sites).done:
            break
    assert sites.checked == ["BOIS & CO"]  # l'enseigne, pas la raison sociale
