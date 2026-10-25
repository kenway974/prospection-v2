"""C40, C41 : pannes pendant une campagne (Google occupé, refus, plantage, page illisible)."""

import contextlib
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import Engine

from prospection.application import campaign_step
from prospection.application.campaign_step import run_step
from prospection.application.campaigns import create_campaign, progress
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place, pages, request
from tests.application.test_campaign_step import run_all, usage
from tests.fake_http import fake_client


def test_busy_retried_then_skipped(campaign_db: Engine) -> None:
    client, _ = fake_client(lambda r: httpx.Response(429, json={}))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    outcomes = [run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW) for _ in range(5)]
    assert [o.retry_at for o in outcomes[:4]] == [
        NOW + timedelta(seconds=5),
        NOW + timedelta(seconds=30),
        NOW + timedelta(seconds=120),
        None,
    ]
    assert outcomes[4].done
    assert progress(campaign_db, campaign_id).stop_reason is not None


def test_refused_stops_with_message(campaign_db: Engine) -> None:
    client, _ = fake_client(lambda r: httpx.Response(403, json={"error": {}}))
    campaign_id = create_campaign(campaign_db, request(), NOW)
    assert run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW).done
    assert "Places API (New)" in (progress(campaign_db, campaign_id).stop_reason or "")


def test_C40_rerun_after_crash_does_not_double_count_prospects(campaign_db: Engine) -> None:
    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("le worker s'arrête en plein appel")
        return httpx.Response(200, json={"places": [api_place(1), api_place(2)]})

    client, _ = fake_client(flaky)
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    with contextlib.suppress(RuntimeError):
        run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.found, state.qualified) == (2, 2)
    assert usage(campaign_db) == (2, 0)  # l'appel interrompu a pu avoir lieu : compté (prudent)


def test_C37_missing_google_key_stops_with_reason(campaign_db: Engine) -> None:
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")
    client, recorder = fake_client(pages([api_place(1)]))
    campaign_id = create_campaign(campaign_db, request(), NOW)
    assert run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW).done
    assert recorder.requests == []
    assert progress(campaign_db, campaign_id).stop_reason == (
        "Clé Google absente ou illisible : ajoutez-la dans Réglages → Clés API."
    )


def test_C41_control_characters_in_google_text_do_not_lose_the_page(campaign_db: Engine) -> None:
    dirty = api_place(1, name="Cuisines\u0000Martin\u0007")
    client, recorder = fake_client(pages([dirty, api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=2), NOW)
    run_all(campaign_db, campaign_id, client)
    assert progress(campaign_db, campaign_id).qualified == 2
    assert len(recorder.requests) == 1
    with campaign_db.connect() as conn:
        names = conn.exec_driver_sql("SELECT data_json->>'name' FROM prospects ORDER BY id")
        assert [n for (n,) in names] == ["Cuisines Martin", "Cuisines Martin 2"]


def test_C41_unexpected_error_saving_a_page_retried_then_skipped(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: object) -> None:
        raise RuntimeError("base indisponible")

    monkeypatch.setattr(campaign_step, "save_page", broken)
    client, recorder = fake_client(pages([api_place(1)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    outcomes = [run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW) for _ in range(5)]
    assert [o.retry_at is not None for o in outcomes[:3]] == [True, True, True]
    assert outcomes[3].retry_at is None and not outcomes[3].done
    assert outcomes[4].done
    assert len(recorder.requests) == 4  # 4 essais puis la page est ignorée : plus aucun appel
    events = [e.message for e in progress(campaign_db, campaign_id).recent_events]
    assert "Page de résultats impossible à enregistrer : page ignorée" in events


def test_C41_request_refused_by_google_skips_only_that_page(campaign_db: Engine) -> None:
    answers = iter([
        httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT"}}),
        httpx.Response(200, json={"places": [api_place(1)]}),
    ])  # fmt: skip
    client, _ = fake_client(lambda r: next(answers))
    two_trades = request(target=1, trades=("cuisiniste", "fleuriste"))
    campaign_id = create_campaign(campaign_db, two_trades, NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert state.stop_reason == "Objectif atteint : 1 prospect qualifié."
    assert "Requête refusée par Google : page ignorée" in [e.message for e in state.recent_events]


def test_C40_results_and_next_page_saved_together_or_not_at_all(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    from prospection.application import page_results

    def crash_at_the_end(*args: object) -> None:
        raise RuntimeError("coupure juste avant la fin de l'enregistrement")

    monkeypatch.setattr(page_results, "add_counts", crash_at_the_end)
    client, _ = fake_client(pages([api_place(1)], [api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW)
    with campaign_db.connect() as conn:
        saved = conn.exec_driver_sql("SELECT count(*) FROM prospects").scalar_one()
        page = conn.exec_driver_sql("SELECT page_number FROM campaign_steps").scalar_one()
    assert (saved, page) == (0, 0)  # rien d'enregistré : la page sera relue en entier


def test_C41_unexpected_error_reading_google_retried_then_skipped(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    def deep_json(*args: object) -> None:
        raise RecursionError("JSON trop imbriqué")

    monkeypatch.setattr(campaign_step, "search_page", deep_json)
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    client, _ = fake_client(pages())
    outcomes = [run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW) for _ in range(5)]
    assert [o.retry_at is not None for o in outcomes[:3]] == [True, True, True]
    assert outcomes[4].done and usage(campaign_db) == (4, 0)
