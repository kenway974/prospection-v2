"""C134 : les villes proposées arrivent pendant la frappe ; une lettre ne lance rien."""

from fastapi.testclient import TestClient

from tests.ui.test_search_form import client, text

__all__ = ["client"]  # fixture partagée


def test_C134_cities_suggested_while_typing(client: TestClient) -> None:
    page = text(client.get("/recherche"))
    assert 'hx-trigger="input changed delay:400ms"' in page  # pas en quittant le champ
    assert 'id="communes-attente" class="htmx-indicator secondary">Recherche des villes…' in page


def test_C134_one_letter_is_not_searched(client: TestClient) -> None:
    fragment = text(client.get("/recherche/communes", params={"ville": "P", "pays": "BE"}))
    assert fragment.strip() == '<p class="secondary">Tapez au moins 2 lettres.</p>'


def test_C134_first_city_checked_only_when_alone(client: TestClient) -> None:
    several = text(client.get("/recherche/communes", params={"ville": "Saint", "pays": "BE"}))
    assert several.count('name="commune"') > 1 and "checked" not in several
    alone = text(client.get("/recherche/communes", params={"ville": "Namur", "pays": "BE"}))
    assert alone.count('name="commune"') == 1 and "checked" in alone
