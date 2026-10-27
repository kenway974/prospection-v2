"""C44, C93 : API Recherche d'entreprises (gratuite, sans clé)."""

from datetime import date

import httpx
import pytest

from prospection.sources.company_registry import (
    RegistryRejected,
    RegistryUnavailable,
    search_companies,
)
from tests.fake_http import fake_client, json_reply, timeout


def result(**changes: object) -> dict[str, object]:
    base: dict[str, object] = {
        "siren": "912345678", "nom_complet": "CUISINES MARTIN",
        "nom_raison_sociale": "CUISINES MARTIN",
        "date_creation": "2022-03-01", "etat_administratif": "A", "nature_juridique": "5710",
        "activite_principale": "43.32A", "tranche_effectif_salarie": "03", "statut_diffusion": "O",
        "siege": {"siret": "91234567800012", "code_postal": "69002", "libelle_commune": "LYON",
                  "liste_enseignes": ["CUISINES MARTIN LYON"], "nom_commercial": None,
                  "statut_diffusion_etablissement": "O"},
        "dirigeants": [
            {"type_dirigeant": "personne physique", "nom": "DUPONT", "prenoms": "Marie",
             "qualite": "Présidente"},
            {"type_dirigeant": "personne morale", "denomination": "HOLDING M",
             "qualite": "Associé"},
        ],
        "finances": {"2023": {"ca": 400000, "resultat_net": 20000},
                     "2024": {"ca": 450000, "resultat_net": 32000}},
    }  # fmt: skip
    base.update(changes)
    return base


def page(*results: dict[str, object]) -> dict[str, object]:
    return {"results": list(results), "total_results": len(results), "page": 1, "per_page": 5,
            "total_pages": 1}  # fmt: skip


def test_C44_company_read_with_leaders_and_latest_finances() -> None:
    client, recorder = fake_client(json_reply(200, page(result())))
    [company] = search_companies(client, "Cuisines Martin", "69002")
    params = recorder.requests[0].url.params
    assert (params["q"], params["code_postal"]) == ("Cuisines Martin", "69002")
    assert params["etat_administratif"] == "A"  # une entreprise cessée n'est jamais proposée
    assert (company.siren, company.postal_code, company.created) == (
        "912345678",
        "69002",
        date(2022, 3, 1),
    )
    assert company.other_names == ("CUISINES MARTIN LYON",)
    assert company.leaders == ("Marie DUPONT (Présidente)", "HOLDING M (Associé)")
    assert company.finances == (2024, 450000, 32000) and company.diffusible


def test_C93_non_diffusible_keeps_no_personal_data() -> None:
    client, _ = fake_client(json_reply(200, page(result(statut_diffusion="P"))))
    [company] = search_companies(client, "Cuisines Martin", "69002")
    assert not company.diffusible and company.leaders == () and company.finances is None


def test_invalid_results_skipped_missing_fields_unknown() -> None:
    sparse: dict[str, object] = {"siren": "123456789", "nom_complet": "X"}
    client, _ = fake_client(json_reply(200, page(result(), {"siren": 12}, sparse)))
    companies = search_companies(client, "x", None)
    assert [c.siren for c in companies] == ["912345678", "123456789"]
    assert companies[1].created is None and companies[1].postal_code is None


@pytest.mark.parametrize("handler", [json_reply(429, {}), json_reply(500, {}), timeout])
def test_service_down_raises(handler: object) -> None:
    client, _ = fake_client(handler)  # type: ignore[arg-type]
    with pytest.raises(RegistryUnavailable):
        search_companies(client, "x", "69002")


def test_empty_name_asks_nothing() -> None:
    client, recorder = fake_client(lambda r: httpx.Response(200, json=page()))
    assert search_companies(client, "  ", "69002") == [] and recorder.requests == []


def test_C45_matching_shops_kept_with_their_siret() -> None:
    shops = [{"siret": "91234567800020", "code_postal": "69002"}, {"siret": 5}]
    client, _ = fake_client(json_reply(200, page(result(matching_etablissements=shops))))
    [company] = search_companies(client, "Cuisines Martin", "69002")
    assert company.siret == "91234567800012"
    assert company.branches == (("91234567800020", "69002"),)


def test_refused_search_is_not_a_breakdown() -> None:
    client, _ = fake_client(json_reply(400, {"erreur": "trop court"}))
    with pytest.raises(RegistryRejected):
        search_companies(client, "xy", "69002")


def test_leaders_text_neutralized() -> None:
    leader = {"nom": "DUPONT\x1b[31m", "prenoms": "Marie\x00", "qualite": "Gérante\n<b>"}
    client, _ = fake_client(json_reply(200, page(result(dirigeants=[leader]))))
    [company] = search_companies(client, "Cuisines Martin", "69002")
    assert company.leaders == ("Marie DUPONT [31m (Gérante <b>)",)  # <b> échappé à l'affichage
