"""C57, C58, C60 : score, raison et fiabilité visibles dans la liste et sur la fiche."""

import dataclasses

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.config import Settings
from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE
from tests.ui.test_call_screens import client, text

__all__ = ["client"]  # fixture partagée


def test_C57_C58_list_shows_score_and_reason_and_sorts_by_score(
    client: TestClient, campaign_db: Engine
) -> None:
    [pid] = add(campaign_db, dataclasses.replace(PLACE, review_count=4))
    page = text(client.get("/prospects?tri=score"))
    assert "Score (meilleures d'abord)" in page and "sans site, 4 avis, mobile" in page
    assert '<span class="visually-hidden"> sur 100, score d\'opportunité</span>' in page
    assert 'aria-label="Score' not in page  # un <strong> n'annonce pas son aria-label
    card = text(client.get(f"/prospects/{pid}"))
    assert "Détail du score (75/100)" in card and "Très peu d'avis Google (4) : +20" in card
    assert "Téléphone" in card and "sûr" in card
    assert "Téléphone (fiche Google)" in card and "mobile" in card
    assert card.count("06 12 34 56 78") == 1  # une seule fois, au même format
    assert 'href="https://www.linkedin.com/search/results/people/?keywords=' in card


def test_C110_C111_call_sheet_and_health_on_the_card(
    client: TestClient, campaign_db: Engine
) -> None:
    [pid] = add(campaign_db, dataclasses.replace(PLACE, review_count=4))
    page = text(client.get(f"/prospects/{pid}"))
    assert "Pour l'appel" in page and "Indices à confirmer pendant l'appel" in page
    assert "Santé de l'entreprise" in page and "rythme non disponible" in page


def test_C110_invalid_rules_stop_the_start(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, campaign_db: Engine
) -> None:
    from prospection.domain import call_sheet
    from prospection.ui import app as app_module

    assert call_sheet.load_rules()  # le fichier livré est valide

    def broken() -> None:
        raise call_sheet.InvalidRules("règle invalide")

    monkeypatch.setattr(app_module, "load_rules", broken)
    with pytest.raises(call_sheet.InvalidRules):
        app_module.create_app(settings, campaign_db)


def test_C62_C63_C66_campaign_exports_downloadable(client: TestClient, campaign_db: Engine) -> None:
    add(campaign_db, PLACE)
    with campaign_db.connect() as conn:
        campaign_id = int(conn.exec_driver_sql("SELECT max(id) FROM campaigns").scalar_one())
    page = text(client.get(f"/campagnes/{campaign_id}"))
    assert f'href="/campagnes/{campaign_id}/export.xlsx"' in page
    csv_file = client.get(f"/campagnes/{campaign_id}/export.csv?liste=exclus")
    assert csv_file.headers["content-type"].startswith("text/csv")
    assert "attachment" in csv_file.headers["content-disposition"]
    xlsx = client.get(f"/campagnes/{campaign_id}/export.xlsx")
    assert xlsx.content[:2] == b"PK" and xlsx.status_code == 200
    assert client.get("/campagnes/999999/export.xlsx").status_code == 404
