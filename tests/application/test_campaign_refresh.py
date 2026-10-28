"""C76 : mettre à jour une campagne passée (fermés, changements de site…)."""

import dataclasses

import httpx
from sqlalchemy import Engine

from prospection.application.campaign_refresh import refresh_info, refresh_next, request_refresh
from prospection.application.prospect_card import card
from prospection.storage.alerts import unseen_alerts
from prospection.storage.campaigns import recent_events, set_status
from tests.application.campaign_helpers import BOX, NOW, PRICING
from tests.application.test_call_tracking import PARIS, add
from tests.fake_http import fake_client
from tests.storage.test_campaigns import PLACE

SHOP = dataclasses.replace(PLACE, place_id="p2", name="Boutique")


def google(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/p1"):
        body = {"id": "p1", "displayName": {"text": "Atelier"}, "businessStatus":
                "CLOSED_PERMANENTLY", "internationalPhoneNumber": "+33612345678"}  # fmt: skip
        return httpx.Response(200, json=body)
    if request.url.path.endswith("/p2"):
        body = {
            "id": "p2",
            "displayName": {"text": "Boutique"},
            "businessStatus": "OPERATIONAL",
            "internationalPhoneNumber": "+33612345678",
            "websiteUri": "https://boutique.fr",
        }
        return httpx.Response(200, json=body)
    return httpx.Response(404, json={})


def done_campaign(engine: Engine) -> list[int]:
    ids = add(engine, PLACE, SHOP)
    with engine.begin() as conn:
        set_status(conn, 1, "done", NOW, "Objectif atteint : 2 prospects qualifiés.")
    return ids


def test_C76_cost_shown_before_launching(campaign_db: Engine) -> None:
    done_campaign(campaign_db)
    info = refresh_info(campaign_db, PRICING, 1, NOW)
    assert info.places == 2 and info.pending == 0 and info.cost.free_pages == 2


def test_C76_each_place_reread_and_changes_logged(campaign_db: Engine) -> None:
    first, second = done_campaign(campaign_db)
    assert request_refresh(campaign_db, 1, NOW) == 2
    client, seen = fake_client(google)
    assert refresh_next(campaign_db, BOX, client, PRICING, NOW)
    assert refresh_next(campaign_db, BOX, client, PRICING, NOW)
    assert not refresh_next(campaign_db, BOX, client, PRICING, NOW)  # rien payé en double
    assert len(seen.requests) == 2
    with campaign_db.connect() as conn:
        messages = [e.message for e in recent_events(conn, 1, 10)]
        [alert] = unseen_alerts(conn)
    assert "Atelier : Fermé définitivement" in messages
    assert "Boutique : Site ajouté" in messages and alert.kind == "maj"
    assert card(campaign_db, second, NOW, PARIS).prospect.data["website"] == "https://boutique.fr"
    with campaign_db.connect() as conn:
        query = "SELECT qualified, status, reasons FROM prospects WHERE id = %(id)s"
        closed = conn.exec_driver_sql(query, {"id": first})
        assert closed.one() == (False, None, ["Fermé définitivement"])  # plus à appeler


def test_C76_only_finished_campaigns_and_stops_without_key(campaign_db: Engine) -> None:
    add(campaign_db, PLACE)
    assert request_refresh(campaign_db, 1, NOW) == 0  # encore en cours
    with campaign_db.begin() as conn:
        set_status(conn, 1, "done", NOW, "fini")
        conn.exec_driver_sql("DELETE FROM api_keys")
    request_refresh(campaign_db, 1, NOW)
    client, seen = fake_client(google)
    assert refresh_next(campaign_db, BOX, client, PRICING, NOW)
    assert seen.requests == []
    with campaign_db.connect() as conn:
        messages = [e.message for e in recent_events(conn, 1, 5)]
        [alert] = unseen_alerts(conn)
    assert any(m.startswith("Mise à jour arrêtée : clé Google absente") for m in messages)
    assert (
        "Mise à jour terminée" not in messages and "arrêtée" in alert.message
    )  # jamais « terminée »
