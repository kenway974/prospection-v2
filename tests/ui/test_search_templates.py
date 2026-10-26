"""C18 : un modèle existant n'est jamais écrasé sans prévenir."""

from fastapi.testclient import TestClient

from tests.ui.test_search_form import client, post, text

__all__ = ["client"]  # fixture partagée


def test_C18_template_name_taken_refused_and_nothing_launched(client: TestClient) -> None:
    assert post(client, modele="Cuisinistes 974").status_code == 303
    response = post(client, modele=" cuisinistes 974 ", nombre="5")
    assert response.status_code == 400
    assert "Un modèle porte déjà ce nom : choisissez-en un autre." in text(response)
    page = text(client.get("/recherche"))
    assert page.count('href="/campagnes/') == 1
    assert 'href="/recherche?modele=Cuisinistes%20974"' in page
