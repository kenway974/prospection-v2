"""C94, C95 : écrans de confidentialité et suppression d'une entreprise."""

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE
from tests.ui.test_call_screens import client, text
from tests.ui.test_search_form import ORIGIN

__all__ = ["client"]  # fixture partagée


def test_C94_purge_duration_setting(client: TestClient) -> None:
    assert 'value="6"' in text(client.get("/reglages/confidentialite"))
    client.post("/reglages/confidentialite", data={"mois": "12"}, headers=ORIGIN)
    assert 'value="12"' in text(client.get("/reglages/confidentialite"))
    bad = client.post("/reglages/confidentialite", data={"mois": "36"}, headers=ORIGIN)
    assert bad.status_code == 400 and "entre 1 et 24" in text(bad)


def test_C95_erase_from_the_card_after_confirmation(
    client: TestClient, campaign_db: Engine
) -> None:
    [pid] = add(campaign_db, PLACE)
    assert f"/prospects/{pid}/supprimer" in text(client.get(f"/prospects/{pid}"))
    assert "Atelier" in text(client.get(f"/prospects/{pid}/supprimer"))
    done = client.post(f"/prospects/{pid}/supprimer", headers=ORIGIN, follow_redirects=False)
    assert done.headers["location"] == "/reglages/confidentialite?supprime=1"
    assert "ne sera plus jamais reprise" in text(client.get(done.headers["location"]))
    assert client.get(f"/prospects/{pid}").status_code == 404
    assert client.post(f"/prospects/{pid}/supprimer", headers=ORIGIN).status_code == 404
