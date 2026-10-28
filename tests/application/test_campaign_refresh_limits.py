"""C76 : la mise à jour respecte le budget, ne paie rien deux fois et s'arrête proprement."""

import dataclasses

import httpx
from sqlalchemy import Engine

from prospection.application.call_actions import schedule
from prospection.application.campaign_refresh import refresh_info, refresh_next, request_refresh
from prospection.storage.alerts import unseen_alerts
from prospection.storage.campaigns import load_campaign, recent_events
from prospection.storage.refresh import take_refresh
from tests.application.campaign_helpers import BOX, NOW, PRICING
from tests.application.test_call_tracking import PARIS
from tests.application.test_campaign_refresh import done_campaign, google
from tests.fake_http import fake_client, json_reply


def _events(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        return [e.message for e in recent_events(conn, 1, 10)]


def test_C76_never_queued_twice(campaign_db: Engine) -> None:
    done_campaign(campaign_db)
    assert request_refresh(campaign_db, 1, NOW) == 2
    assert request_refresh(campaign_db, 1, NOW) == 0  # double appui, deux onglets
    assert refresh_info(campaign_db, PRICING, 1, NOW).running


def test_C76_two_workers_never_take_the_same_place(campaign_db: Engine) -> None:
    done_campaign(campaign_db)
    request_refresh(campaign_db, 1, NOW)
    with campaign_db.begin() as first, campaign_db.begin() as second:
        a, b = take_refresh(first, NOW), take_refresh(second, NOW)
    assert a is not None and b is not None and a.prospect_id != b.prospect_id


def test_C76_stops_at_the_budget(campaign_db: Engine) -> None:
    done_campaign(campaign_db)
    request_refresh(campaign_db, 1, NOW)
    with campaign_db.begin() as conn:  # quota gratuit épuisé, plafond à 0 €
        conn.exec_driver_sql("INSERT INTO google_usage VALUES ('2026-10', 1000, 0)")
    client, seen = fake_client(google)
    assert refresh_next(campaign_db, BOX, client, PRICING, NOW)
    assert not refresh_next(campaign_db, BOX, client, PRICING, NOW)  # file vidée
    assert seen.requests == [] and any("plafond Google atteint" in m for m in _events(campaign_db))


def test_C76_busy_place_skipped_refused_key_stops(campaign_db: Engine) -> None:
    done_campaign(campaign_db)
    request_refresh(campaign_db, 1, NOW)
    busy = fake_client(json_reply(503, {}))[0]
    refresh_next(campaign_db, BOX, busy, PRICING, NOW)
    assert "Atelier : fiche non relue (Google trop sollicité)" in _events(campaign_db)
    refused = fake_client(json_reply(403, {"error": {"status": "PERMISSION_DENIED"}}))[0]
    refresh_next(campaign_db, BOX, refused, PRICING, NOW)
    assert any(m.startswith("Mise à jour arrêtée : Google refuse") for m in _events(campaign_db))


def test_C76_closed_shop_leaves_counts_and_follow_ups(campaign_db: Engine) -> None:
    first, _ = done_campaign(campaign_db)
    schedule(campaign_db, first, "rappeler", "2026-10-26", "", NOW, PARIS)
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("UPDATE campaigns SET qualified = 2")
    request_refresh(campaign_db, 1, NOW)
    client, _ = fake_client(google)
    while refresh_next(campaign_db, BOX, client, PRICING, NOW):
        pass
    with campaign_db.connect() as conn:
        assert load_campaign(conn, 1).qualified == 1
        open_actions = conn.exec_driver_sql(
            "SELECT count(*) FROM prospect_actions WHERE done_at IS NULL"
        ).scalar_one()
        assert open_actions == 0 and len(unseen_alerts(conn)) == 1  # une seule « terminée »


def test_C76_unusable_id_never_paid(campaign_db: Engine) -> None:
    from tests.application.test_call_tracking import add
    from tests.storage.test_campaigns import PLACE

    add(campaign_db, dataclasses.replace(PLACE, place_id="a/b"))
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("UPDATE campaigns SET status = 'done'")
    request_refresh(campaign_db, 1, NOW)
    client, seen = fake_client(lambda r: httpx.Response(200, json={}))
    refresh_next(campaign_db, BOX, client, PRICING, NOW)
    with campaign_db.connect() as conn:
        assert load_campaign(conn, 1).cost_cents == 0
    assert seen.requests == [] and "Atelier : fiche Google illisible" in _events(campaign_db)
