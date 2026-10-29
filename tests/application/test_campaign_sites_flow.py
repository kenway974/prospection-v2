"""C38, C40, C41 : lecture des sites dans le déroulé d'une campagne (reprise, doublons)."""

import dataclasses

import pytest
from sqlalchemy import Engine

from prospection.application import page_results, registry_step
from prospection.application.campaign_step import run_step
from prospection.application.campaigns import create_campaign, progress
from prospection.application.prospect_listing import prospect_list
from prospection.domain.criteria import Criteria
from prospection.storage.campaign_steps import next_step
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place, pages, request
from tests.application.test_campaign_sites import FakeSites
from tests.fake_http import fake_client


def test_C38_known_place_site_not_read_again(campaign_db: Engine) -> None:
    sites = FakeSites({})
    client, _ = fake_client(pages([api_place(1)], [api_place(1), api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=5), NOW)
    for _ in range(10):
        if run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, sites).done:
            break
    assert sites.checked == ["Cuisines Martin 1", "Cuisines Martin 2"]


def test_C40_cut_during_site_reading_resumes_without_paying_again(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    from prospection.application.site_verdict import read_sites as real

    calls = {"n": 0}

    def cut_once(*args: object) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("worker coupé")
        return real(*args)  # type: ignore[arg-type]

    monkeypatch.setattr(page_results, "read_sites", cut_once)
    client, recorder = fake_client(pages([api_place(1), api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=2), NOW)
    for _ in range(10):
        if run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, FakeSites({})).done:
            break
    assert len(recorder.requests) == 1 and progress(campaign_db, campaign_id).qualified == 2


def test_I2_page_saved_twice_counted_once(campaign_db: Engine) -> None:
    """Deux workers sur la même page en attente : la seconde passe ne compte rien."""
    from prospection.application.campaign_step import _fetch_page
    from prospection.application.pending_page import decode_page

    client, _ = fake_client(pages([api_place(1)]))
    campaign_id = create_campaign(campaign_db, request(target=5), NOW)
    with campaign_db.connect() as conn:
        step = next_step(conn, campaign_id)
    assert step is not None
    _fetch_page(campaign_db, BOX, client, PRICING, campaign_id, step, NOW)
    with campaign_db.connect() as conn:
        pending = next_step(conn, campaign_id)
    assert pending is not None and pending.pending_page is not None
    page = decode_page(pending.pending_page)
    page_results.save_page(campaign_db, campaign_id, pending, page, NOW)
    page_results.save_page(campaign_db, campaign_id, pending, page, NOW)
    assert progress(campaign_db, campaign_id).found == 1
    with campaign_db.connect() as conn:
        numbers = conn.exec_driver_sql("SELECT page_number FROM campaign_steps ORDER BY id")
        assert next(n for (n,) in numbers) == 1  # une page lue, pas deux


def test_M8_no_more_sites_read_than_prospects_still_wanted(campaign_db: Engine) -> None:
    sites = FakeSites({})
    client, _ = fake_client(pages([api_place(1), api_place(2), api_place(3)]))
    campaign_id = create_campaign(campaign_db, request(target=1), NOW)
    run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, sites)
    assert len(sites.checked) == 1


def test_I2_long_registry_step_resumes_later(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Étape « registre » trop longue : interrompue, reprise au tour suivant, rien en double."""
    from tests.application.test_registry_campaign import with_insee_key
    from tests.application.test_registry_rules import default_request, services
    from tests.sources.test_sirene_search import etab

    monkeypatch.setattr(registry_step, "STEP_SECONDS", 0.0)
    with_insee_key(campaign_db)
    companies = [etab(siren=f"40000000{n}") for n in range(3)]
    campaign_id = create_campaign(campaign_db, default_request(), NOW)
    client = services(companies, [])
    outcomes = [run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW, FakeSites({}))
                for _ in range(6)]  # fmt: skip
    assert not outcomes[0].done
    assert len(prospect_list(campaign_db, None, "", "trouves").rows) == 3
    assert progress(campaign_db, campaign_id).found == 3


def test_M4_old_or_broken_site_report_never_breaks_the_list(campaign_db: Engine) -> None:
    from tests.application.test_call_tracking import add
    from tests.storage.test_campaigns import PLACE

    add(campaign_db, PLACE, dataclasses.replace(PLACE, place_id="p2"))
    with campaign_db.begin() as conn:
        conn.exec_driver_sql(
            """UPDATE prospects SET site_json = '{"origin": "fiche Google", "audit": {"score": 4}}'
               WHERE place_id = 'p1'"""
        )
    rows = prospect_list(campaign_db, None, "", "trouves").rows
    assert len(rows) == 2 and all(r.site is None for r in rows)


def test_stale_campaigns_wait_long_enough_for_site_reading() -> None:
    from datetime import timedelta

    from prospection.application.campaign_queue import STALE_AFTER

    assert timedelta(minutes=10) <= STALE_AFTER
    assert Criteria().max_site_score is None
