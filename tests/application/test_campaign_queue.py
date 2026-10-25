"""C40 : une campagne coupée reprend ; deux workers ne prennent jamais la même."""

from datetime import timedelta

from sqlalchemy import Engine, text

from prospection.application.campaign_queue import claim_next, release_until
from prospection.application.campaigns import create_campaign, progress
from tests.application.campaign_helpers import NOW, request


def test_queued_campaign_is_claimed_once(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    assert claim_next(campaign_db, NOW) == campaign_id
    assert progress(campaign_db, campaign_id).status == "running"
    assert claim_next(campaign_db, NOW) is None


def test_two_workers_never_claim_the_same_campaign(campaign_db: Engine) -> None:
    first = create_campaign(campaign_db, request(), NOW)
    second = create_campaign(campaign_db, request(), NOW)
    claims = {claim_next(campaign_db, NOW), claim_next(campaign_db, NOW)}
    assert claims == {first, second}


def test_C40_stale_running_campaign_is_reclaimed(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    claim_next(campaign_db, NOW)
    assert claim_next(campaign_db, NOW + timedelta(minutes=1)) is None
    assert claim_next(campaign_db, NOW + timedelta(minutes=3)) == campaign_id


def test_campaign_waiting_for_retry_is_not_claimed_before_time(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    claim_next(campaign_db, NOW)
    release_until(campaign_db, campaign_id, NOW + timedelta(seconds=30))
    assert claim_next(campaign_db, NOW + timedelta(seconds=10)) is None
    assert claim_next(campaign_db, NOW + timedelta(seconds=31)) == campaign_id


def test_done_campaign_is_never_claimed(campaign_db: Engine) -> None:
    campaign_id = create_campaign(campaign_db, request(), NOW)
    with campaign_db.begin() as conn:
        conn.execute(
            text("UPDATE campaigns SET status = 'done' WHERE id = :id"), {"id": campaign_id}
        )
    assert claim_next(campaign_db, NOW + timedelta(hours=1)) is None
