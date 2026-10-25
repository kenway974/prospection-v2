"""C121, C122 : chercher en Belgique, Suisse, Luxembourg ou Monaco depuis l'écran Recherche."""

import pytest
from fastapi.testclient import TestClient

from prospection.domain.campaign_request import (
    CampaignRequest,
    CityZone,
    DepartmentZone,
    RadiusZone,
    Zone,
)
from prospection.domain.criteria import Criteria
from prospection.ui.search_form import commune_value, parse_form, request_to_form
from tests.ui.test_search_form import FORM, client, post, text

__all__ = ["client"]  # fixture partagée
GENEVA = CityZone("Genève", "GE", 46.2022, 6.1457, "CH")


def test_C121_country_list_with_france_first(client: TestClient) -> None:
    page = text(client.get("/recherche"))
    assert '<label for="pays">Pays</label>' in page
    assert '<option value="FR" selected>France</option>' in page
    assert '<option value="BE">Belgique</option>' in page


def test_C122_foreign_city_found_without_calling_the_french_service(client: TestClient) -> None:
    fragment = text(client.get("/recherche/communes", params={"ville": "Genève", "pays": "CH"}))
    assert "Genève (Genève, Suisse)" in fragment and "Saint-Denis" not in fragment


def test_C122_foreign_city_and_canton_become_zones() -> None:
    form = {**FORM, "pays": "CH", "commune": commune_value(GENEVA), "departements": "Vaud"}
    parsed = parse_form(form)
    assert parsed.errors == {}
    assert parsed.raw.zones == [GENEVA, DepartmentZone("VD", "Canton de Vaud", "CH")]


def test_C122_canton_of_another_country_refused() -> None:
    parsed = parse_form({**FORM, "pays": "BE", "commune": "", "departements": "Vaud"})
    assert parsed.errors["zones"] == (
        "Province inconnue en Belgique : Vaud. Exemple : Liège, Hainaut."
    )


def test_C121_unknown_country_refused(client: TestClient) -> None:
    response = post(client, pays="XX")
    assert response.status_code == 400
    assert "Choisissez un pays de la liste." in text(response)


def test_C122_country_change_refreshes_the_city_choices(client: TestClient) -> None:
    page = text(client.get("/recherche"))
    assert 'id="pays" name="pays" hx-get="/recherche/communes"' in page


@pytest.mark.parametrize(
    "commune",
    ["CH|GE|0|0|Nulle part", "CH|VD|46.2022|6.1457|Genève", "FR||0|0|Nulle part",
     "BE|BRU|50.8505|4.3488|Genève"],
)  # fmt: skip
def test_C13_tampered_city_refused(commune: str) -> None:
    pays = commune[:2]
    parsed = parse_form({**FORM, "pays": pays, "commune": commune})
    assert parsed.errors["zones"] == "Choisissez la commune dans la liste."


def test_C122_city_of_another_country_says_so() -> None:
    parsed = parse_form({**FORM, "pays": "BE", "commune": commune_value(GENEVA)})
    assert parsed.errors["zones"] == (
        "Cette ville n'est pas dans le pays choisi : cherchez-la à nouveau."
    )


@pytest.mark.parametrize(
    "zones",
    [
        (GENEVA, DepartmentZone("FR", "Canton de Fribourg", "CH")),
        (RadiusZone(CityZone("Liège", "WAL", 50.6337, 5.5675, "BE"), 20),
         DepartmentZone("WLX", "Province de Luxembourg", "BE")),
        (DepartmentZone("ME", "Canton de Mersch", "LU"),),
        (CityZone("Monaco", "", 43.7372, 7.4215, "MC"),),
    ],
)  # fmt: skip
def test_C18_C121_foreign_template_reloads_the_same_zones(zones: tuple[Zone, ...]) -> None:
    request = CampaignRequest("Modèle", ("cuisiniste",), zones, 10, Criteria(), True)
    assert tuple(parse_form(request_to_form(request)).raw.zones) == zones
