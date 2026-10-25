"""C121, C122 : chercher en Belgique, Suisse, Luxembourg ou Monaco depuis l'écran Recherche."""

from fastapi.testclient import TestClient

from prospection.domain.campaign_request import CityZone, DepartmentZone
from prospection.ui.search_form import commune_value, parse_form
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
    assert "Genève (CH-GE)" in fragment and "Saint-Denis" not in fragment


def test_C122_foreign_city_and_canton_become_zones() -> None:
    form = {**FORM, "pays": "CH", "commune": commune_value(GENEVA), "departements": "Vaud"}
    parsed = parse_form(form)
    assert parsed.errors == {}
    assert parsed.raw.zones == [GENEVA, DepartmentZone("VD", "Canton de Vaud", "CH")]


def test_C122_canton_of_another_country_refused() -> None:
    parsed = parse_form({**FORM, "pays": "BE", "commune": "", "departements": "Vaud"})
    assert parsed.errors["zones"] == "Province ou canton inconnu en Belgique : Vaud."


def test_C121_unknown_country_refused(client: TestClient) -> None:
    response = post(client, pays="XX")
    assert response.status_code == 400
    assert "Choisissez un pays de la liste." in text(response)
