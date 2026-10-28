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
