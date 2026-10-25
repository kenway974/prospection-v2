"""C34 à C41, C79 : une campagne avance page par page et s'arrête au bon moment."""

import contextlib
from datetime import timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.campaign_step import run_step
from prospection.application.campaigns import create_campaign, progress, request_stop
from prospection.domain.campaign_request import CampaignRequest, RadiusZone
from prospection.domain.criteria import Criteria
from prospection.storage.google_usage import month_usage
from tests.application.campaign_helpers import (
    BOX,
    LYON,
    NOW,
    PRICING,
    api_place,
    pages,
    request,
)
from tests.fake_http import fake_client

TZ = "Europe/Paris"


def run_all(engine: Engine, campaign_id: int, client: httpx.Client, limit: int = 20) -> None:
    for _ in range(limit):
        if run_step(engine, BOX, client, PRICING, campaign_id, NOW, TZ).done:
            return
    raise AssertionError("la campagne ne s'arrête pas")


def usage(engine: Engine) -> tuple[int, int]:
    with engine.connect() as conn:
        return month_usage(conn, "2026-10")


def test_C36_continues_until_target(campaign_db: Engine) -> None:
    client, recorder = fake_client(
        pages([api_place(1), api_place(2)], [api_place(3), api_place(4)])
    )
    campaign_id = create_campaign(campaign_db, request(target=3), NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.status, state.qualified, state.found) == ("done", 4, 4)
    assert state.stop_reason == "Objectif atteint : 4 prospects qualifiés."
    assert len(recorder.requests) == 2


def test_C37_stops_when_source_exhausted_with_reason(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1, reviews=99), api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=5), NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert state.stop_reason == (
        "Plus de résultats sur Google Maps pour ces métiers et cette zone "
        "(1 qualifié sur 5 voulus)."
    )
    assert state.exclusion_counts == [("Trop d'avis", 1)]


def test_C37_C07_stops_at_free_quota_with_reason_and_keeps_prospects(campaign_db: Engine) -> None:
    with campaign_db.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO google_usage (month, calls, cost_cents) VALUES ('2026-10', 999, 0)"
        )
    client, recorder = fake_client(pages([api_place(1)], [api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=5), NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert state.stop_reason == (
        "Quota gratuit de Google atteint pour ce mois (plafond 0 €). Relevez le plafond "
        "dans Réglages → Budget Google, ou attendez le 1er du mois."
    )
    assert (state.qualified, len(recorder.requests), usage(campaign_db)) == (1, 1, (1000, 0))


def test_C35_stop_keeps_found(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1)], [api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=5), NOW)
    run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, TZ)
    request_stop(campaign_db, campaign_id, NOW)
    assert run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, TZ).done
    state = progress(campaign_db, campaign_id)
    assert (state.status, state.qualified, state.stop_reason) == (
        "done",
        1,
        "Arrêtée à votre demande : les prospects trouvés sont gardés.",
    )


def test_C38_duplicate_across_keywords_counted_once(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1)], [api_place(1), api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    run_all(campaign_db, campaign_id, client)
    assert progress(campaign_db, campaign_id).found == 2


def test_C41_bad_place_does_not_stop(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([{"id": "sans-nom"}, api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert state.qualified == 1
    assert any("1 établissement illisible ignoré" in e.message for e in state.recent_events)


def test_busy_retried_then_skipped(campaign_db: Engine) -> None:
    client, _ = fake_client(lambda r: httpx.Response(429, json={}))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    outcomes = [run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, TZ) for _ in range(4)]
    assert [o.retry_at for o in outcomes[:3]] == [
        NOW + timedelta(seconds=5),
        NOW + timedelta(seconds=30),
        None,
    ]
    assert outcomes[3].done
    assert progress(campaign_db, campaign_id).stop_reason is not None


def test_refused_stops_with_message(campaign_db: Engine) -> None:
    client, _ = fake_client(lambda r: httpx.Response(403, json={"error": {}}))
    campaign_id = create_campaign(campaign_db, request(), NOW)
    assert run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, TZ).done
    assert "Places API (New)" in (progress(campaign_db, campaign_id).stop_reason or "")


def test_C79_cost_recorded_per_campaign(campaign_db: Engine) -> None:
    with campaign_db.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO google_usage (month, calls, cost_cents) VALUES ('2026-10', 1000, 0)"
        )
        conn.exec_driver_sql("UPDATE app_settings SET google_budget_cents = 500")
    client, _ = fake_client(pages([api_place(1)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    run_all(campaign_db, campaign_id, client)
    assert progress(campaign_db, campaign_id).cost_cents == 4
    assert usage(campaign_db) == (1001, 4)


def test_C40_rerun_after_crash_does_not_double_count(campaign_db: Engine) -> None:
    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("le worker s'arrête en plein appel")
        return httpx.Response(200, json={"places": [api_place(1), api_place(2)]})

    client, _ = fake_client(flaky)
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    with contextlib.suppress(RuntimeError):
        run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, TZ)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.found, state.qualified) == (2, 2)
    assert usage(campaign_db) == (2, 0)


def test_C37_missing_google_key_stops_with_reason(campaign_db: Engine) -> None:
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")
    client, recorder = fake_client(pages([api_place(1)]))
    campaign_id = create_campaign(campaign_db, request(), NOW)
    assert run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, TZ).done
    assert recorder.requests == []
    assert progress(campaign_db, campaign_id).stop_reason == (
        "Clé Google absente ou illisible : ajoutez-la dans Réglages → Clés API."
    )


def test_C13_place_outside_radius_excluded(campaign_db: Engine) -> None:
    far = {**api_place(2), "location": {"latitude": 46.5, "longitude": 4.83}}
    client, _ = fake_client(pages([api_place(1), far]))
    radius_request = CampaignRequest(
        "Test", ("cuisiniste",), (RadiusZone(LYON, 15),), 9, Criteria(phone="any"), False
    )
    campaign_id = create_campaign(campaign_db, radius_request, NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.qualified, state.exclusion_counts) == (1, [("Hors zone", 1)])
