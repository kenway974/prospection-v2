"""C24 à C27, C93 : entreprises récemment créées (API Sirene de l'INSEE)."""

from datetime import date

import pytest

from prospection.sources.company_registry import RegistryUnavailable
from prospection.sources.sirene_search import RecentQuery, recent_companies, sirene_q
from tests.fake_http import fake_client, json_reply

QUERY = RecentQuery(date(2026, 7, 28), date(2026, 10, 26), "departement", "69", ("43.32", "47.59"))


def etab(**changes: object) -> dict[str, object]:
    base: dict[str, object] = {
        "siren": "923456789", "siret": "92345678900015", "statutDiffusionEtablissement": "O",
        "dateCreationEtablissement": "2026-09-14", "trancheEffectifsEtablissement": "NN",
        "uniteLegale": {"denominationUniteLegale": "ATELIER BOIS",
                        "categorieJuridiqueUniteLegale": "5720"},
        "adresseEtablissement": {"codePostalEtablissement": "69003",
                                 "libelleCommuneEtablissement": "LYON"},
        "periodesEtablissement": [
            {"dateFin": None, "etatAdministratifEtablissement": "A",
             "activitePrincipaleEtablissement": "43.32A", "enseigne1Etablissement": "BOIS & CO"},
        ],
    }  # fmt: skip
    base.update(changes)
    return base


def test_C24_C25_C27_query_built_for_the_official_syntax() -> None:
    assert sirene_q(QUERY) == (
        "dateCreationEtablissement:[2026-07-28 TO 2026-10-26] AND codeCommuneEtablissement:69* "
        "AND statutDiffusionEtablissement:O AND periode(etatAdministratifEtablissement:A) "
        "AND (periode(activitePrincipaleEtablissement:43.32*) "
        "OR periode(activitePrincipaleEtablissement:47.59*))"
    )
    commune = RecentQuery(date(2026, 7, 28), date(2026, 10, 26), "commune", "97411", ())
    assert "codeCommuneEtablissement:97411" in sirene_q(commune)
    corse = RecentQuery(date(2026, 7, 28), date(2026, 10, 26), "departement", "2A", ())
    assert "codeCommuneEtablissement:2A*" in sirene_q(corse)  # pas la Haute-Corse (20…)


@pytest.mark.parametrize(
    ("commune", "expected"),
    [("75056", "751*"), ("69123", "6938*"), ("13055", "132*"), ("69003", "69003")],
)
def test_C25_big_cities_cover_their_arrondissements(commune: str, expected: str) -> None:
    """Sirène range les établissements de Paris, Lyon et Marseille par arrondissement."""
    query = RecentQuery(date(2026, 7, 28), date(2026, 10, 26), "commune", commune, ())
    assert f"codeCommuneEtablissement:{expected} " in sirene_q(query)


def test_C24_companies_read_with_cursor() -> None:
    body = {"header": {"total": 1, "curseurSuivant": "AoE"}, "etablissements": [etab()]}
    client, recorder = fake_client(json_reply(200, body))
    page = recent_companies(client, "cle", QUERY, "*")
    request = recorder.requests[0]
    assert request.headers["X-INSEE-Api-Key-Integration"] == "cle"
    assert (request.url.params["curseur"], request.url.params["nombre"]) == ("*", "20")
    [company] = page.companies
    assert (company.siren, company.name, company.other_names) == (
        "923456789",
        "ATELIER BOIS",
        ("BOIS & CO",),
    )
    assert (company.created, company.naf, company.postal_code) == (
        date(2026, 9, 14),
        "43.32A",
        "69003",
    )
    assert page.next_cursor == "AoE"


def test_last_page_has_no_next_cursor() -> None:
    body = {"header": {"total": 1, "curseur": "AoE", "curseurSuivant": "AoE"}, "etablissements": []}
    client, _ = fake_client(json_reply(200, body))
    assert recent_companies(client, "cle", QUERY, "AoE").next_cursor is None


def test_C93_non_diffusible_never_proposed() -> None:
    body = {"header": {"total": 1}, "etablissements": [etab(statutDiffusionEtablissement="P")]}
    client, _ = fake_client(json_reply(200, body))
    assert recent_companies(client, "cle", QUERY, "*").companies == []


def test_individual_entrepreneur_named_from_person() -> None:
    person = etab(uniteLegale={"nomUniteLegale": "DUPONT", "prenom1UniteLegale": "MARIE"})
    body = {"header": {"total": 1}, "etablissements": [person]}
    client, _ = fake_client(json_reply(200, body))
    assert recent_companies(client, "cle", QUERY, "*").companies[0].name == "MARIE DUPONT"


def test_no_result_is_an_empty_page() -> None:
    client, _ = fake_client(
        json_reply(404, {"header": {"statut": 404, "message": "Aucun élément"}})
    )
    page = recent_companies(client, "cle", QUERY, "*")
    assert page.companies == [] and page.next_cursor is None


@pytest.mark.parametrize("status", [429, 500, 503])
def test_busy_service_raises(status: int) -> None:
    client, _ = fake_client(json_reply(status, {}))
    with pytest.raises(RegistryUnavailable):
        recent_companies(client, "cle", QUERY, "*")


def test_refused_key_says_what_to_do() -> None:
    from prospection.sources.sirene_search import SireneRefused

    client, _ = fake_client(json_reply(401, {}))
    with pytest.raises(SireneRefused, match="Réglages → Clés API"):
        recent_companies(client, "cle", QUERY, "*")
