"""C151 : page publique de l'app et de sa politique de confidentialité (écran Google)."""

import html

from fastapi.testclient import TestClient


def test_C151_public_page_without_login(client: TestClient) -> None:
    client.cookies.clear()
    response = client.get("/confidentialite-app", follow_redirects=False)
    assert response.status_code == 200
    page = html.unescape(response.text)
    for said in ("Politique de confidentialité", "ne lit jamais le contenu", "désinscri",
                 "gmail.send", "gmail.metadata", "RGPD", "supprim"):  # fmt: skip
        assert said in page, said
    assert 'href="/"' not in page.split("<main")[1]  # pas de menu de l'app hors connexion
