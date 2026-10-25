"""C40 : une campagne coupée reprend ; deux workers ne prennent jamais la même."""

from datetime import timedelta

from sqlalchemy import Engine, text

from prospection.application.campaign_queue import claim_next, release_until
from prospection.application.campaigns import create_campaign, progress
from tests.application.campaign_helpers import NOW, request


def test_queued_campaign_is_claimed_once(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    assert claim_next(campaign_db, NOW, "w1") == campaign_id
    assert progress(campaign_db, campaign_id).status == "running"
    assert claim_next(campaign_db, NOW, "w1") is None


def test_two_workers_never_claim_the_same_campaign(campaign_db: Engine) -> None:
    first = create_campaign(campaign_db, request(), NOW)
    second = create_campaign(campaign_db, request(), NOW)
    with campaign_db.connect() as other_worker, other_worker.begin():
        other_worker.execute(  # un autre worker est en train de prendre la première
            text("SELECT id FROM campaigns WHERE id = :id FOR UPDATE"), {"id": first}
        )
        assert claim_next(campaign_db, NOW, "w2") == second


def test_C40_stale_running_campaign_is_reclaimed(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    claim_next(campaign_db, NOW, "w1")
    assert claim_next(campaign_db, NOW + timedelta(minutes=1), "w2") is None
    assert claim_next(campaign_db, NOW + timedelta(minutes=3), "w2") == campaign_id


def test_campaign_waiting_for_retry_is_not_claimed_before_time(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    claim_next(campaign_db, NOW, "w1")
    release_until(campaign_db, campaign_id, NOW + timedelta(seconds=30), "w1")
    assert claim_next(campaign_db, NOW + timedelta(seconds=10), "w1") is None
    assert claim_next(campaign_db, NOW + timedelta(seconds=31), "w1") == campaign_id


def test_done_campaign_is_never_claimed(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    with campaign_db.begin() as conn:
        conn.execute(
            text("UPDATE campaigns SET status = 'done' WHERE id = :id"), {"id": campaign_id}
        )
    assert claim_next(campaign_db, NOW + timedelta(hours=1), "w1") is None


def test_C40_old_worker_cannot_release_a_campaign_taken_over(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    claim_next(campaign_db, NOW, "w1")
    later = NOW + timedelta(minutes=3)
    assert claim_next(campaign_db, later, "w2") == campaign_id
    release_until(campaign_db, campaign_id, later, "w1")  # w1 se réveille et croit la tenir
    assert claim_next(campaign_db, later, "w3") is None  # toujours à w2


def test_C35_stop_does_not_wait_for_the_retry_pause(campaign_db: Engine) -> None:
    from prospection.application.campaigns import request_stop

    campaign_id = create_campaign(campaign_db, request(), NOW)
    claim_next(campaign_db, NOW, "w1")
    release_until(campaign_db, campaign_id, NOW + timedelta(minutes=2), "w1")  # Google occupé
    request_stop(campaign_db, campaign_id, NOW)
    assert claim_next(campaign_db, NOW, "w1") == campaign_id
