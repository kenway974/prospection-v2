"""C80, C81 : écrans du tableau de bord et du journal."""

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.storage.campaigns import add_counts, add_event
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE
from tests.ui.test_call_screens import client, text

__all__ = ["client"]  # fixture partagée


def test_C80_dashboard(client: TestClient, campaign_db: Engine) -> None:
    assert "Aucune campagne" in text(client.get("/tableau-de-bord"))
    add(campaign_db, PLACE)
    with campaign_db.begin() as conn:
        add_counts(conn, 1, NOW, found=40, excluded=30, qualified=10, cost_cents=350)
    page = text(client.get("/tableau-de-bord"))
    assert "25 % qualifiés" in page and "0,35 € par prospect qualifié" in page


def test_C81_journal_of_a_campaign(client: TestClient, campaign_db: Engine) -> None:
    add(campaign_db, PLACE)
    with campaign_db.begin() as conn:
        add_event(conn, 1, NOW, "warning", "Google trop sollicité : page ignorée")
    page = text(client.get("/campagnes/1/journal"))
    assert "Attention · </strong>Google trop sollicité" in page
    assert client.get("/campagnes/99/journal").status_code == 404


def test_C91_backup_status_on_the_dashboard(client: TestClient, campaign_db: Engine) -> None:
    assert "Sauvegarde quotidienne non configurée" in text(client.get("/tableau-de-bord"))
