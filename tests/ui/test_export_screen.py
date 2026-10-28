"""C67, C74 : relecture avant l'envoi vers Notion, puis bilan."""

import dataclasses

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from tests.application.test_call_tracking import add
from tests.application.test_crm_export import with_notion
from tests.storage.test_campaigns import PLACE
from tests.ui.test_call_screens import client, text
from tests.ui.test_search_form import ORIGIN

__all__ = ["client"]  # fixture partagée


def interested(engine: Engine) -> tuple[int, int]:
    sure, doubtful = add(engine, PLACE, dataclasses.replace(PLACE, place_id="p2", name="Douteux"))
    with engine.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET status = 'intéressé'")
        conn.exec_driver_sql(
            "UPDATE prospects SET to_check = ARRAY['Entreprise à confirmer'] WHERE id = %s",
            (doubtful,),
        )
    return sure, doubtful


def test_C67_review_before_sending_doubtful_unchecked(
    client: TestClient, campaign_db: Engine
) -> None:
    with_notion(campaign_db, client.app.state.box)  # type: ignore[attr-defined]
    sure, doubtful = interested(campaign_db)
    page = text(client.get("/exporter"))
    assert f'name="ids" value="{sure}" checked' in page
    assert f'name="ids" value="{doubtful}">' in page  # « à vérifier » : décoché
    response = client.post("/exporter", data={"ids": [str(sure)]}, headers=ORIGIN,
                           follow_redirects=False)  # fmt: skip
    assert response.status_code == 303, response.text[:300]
    with campaign_db.connect() as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM crm_exports").scalar_one() == 1
    after = text(client.get("/exporter"))
    assert "1 en attente d'envoi" in after


def test_C67_nothing_sent_without_notion(client: TestClient, campaign_db: Engine) -> None:
    interested(campaign_db)
    page = text(client.get("/exporter"))
    assert "Réglages → CRM" in page
