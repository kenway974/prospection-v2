"""C57, C58, C60 : score, raison et fiabilité visibles dans la liste et sur la fiche."""

import dataclasses

from fastapi.testclient import TestClient
from sqlalchemy import Engine

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
    assert "Score d'opportunité 75 sur 100" in page
    card = text(client.get(f"/prospects/{pid}"))
    assert "Détail du score (75/100)" in card and "Très peu d'avis Google (4) : +20" in card
    assert "Téléphone" in card and "sûr" in card
