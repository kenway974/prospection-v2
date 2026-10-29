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
