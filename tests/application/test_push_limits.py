"""Notifications : rien de perdu, rien en double, pause quand le service sature."""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy import Engine

from prospection.application import push
from prospection.application.push import push_job, push_pending
from prospection.storage.push import subscriptions, take_alerts
from tests.application.test_push import DAY, KEYS, PARIS, alert, phone_subscribed
from tests.fake_http import fake_client


def _pending(engine: Engine) -> int:
    with engine.connect() as conn:
        query = "SELECT count(*) FROM alerts WHERE pushed_at IS NULL"
        return int(conn.exec_driver_sql(query).scalar_one())


def test_two_workers_never_take_the_same_alert(campaign_db: Engine) -> None:
    for n in range(3):
        alert(campaign_db, f"a{n}", "nouveaux", DAY)
    with campaign_db.begin() as first, campaign_db.begin() as second:
        a, b = take_alerts(first, DAY, None, limit=2), take_alerts(second, DAY, None, limit=2)
    assert len(a) == 2 and len(b) == 1 and not {x.id for x in a} & {x.id for x in b}


def test_at_most_20_per_pass(campaign_db: Engine) -> None:
    phone_subscribed(campaign_db)
    for n in range(25):
        alert(campaign_db, f"a{n}", "nouveaux", DAY)
    client, _ = fake_client(lambda r: httpx.Response(201))
    assert push_pending(campaign_db, client, KEYS, DAY, PARIS) == 20
    assert _pending(campaign_db) == 5


def test_unexpected_error_gives_every_alert_back(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    phone_subscribed(campaign_db)
    alert(campaign_db, "a1", "nouveaux", DAY)

    def broken(*args: object) -> None:
        raise RuntimeError("panne imprévue")

    monkeypatch.setattr(push, "send_push", broken)
    with pytest.raises(RuntimeError):
        push_pending(campaign_db, fake_client(lambda r: httpx.Response(201))[0], KEYS, DAY, PARIS)
    assert _pending(campaign_db) == 1  # rien de perdu


def test_refused_for_good_or_other_key(campaign_db: Engine) -> None:
    phone_subscribed(campaign_db)
    alert(campaign_db, "a1", "nouveaux", DAY)
    too_big = fake_client(lambda r: httpx.Response(413))[0]
    assert push_pending(campaign_db, too_big, KEYS, DAY, PARIS) == 1  # abandonnée, pas renvoyée
    alert(campaign_db, "a2", "nouveaux", DAY)
    other_key = fake_client(lambda r: httpx.Response(403))[0]
    push_pending(campaign_db, other_key, KEYS, DAY, PARIS)
    with campaign_db.connect() as conn:
        assert subscriptions(conn) == []  # le téléphone devra se réabonner


def test_busy_service_pauses_the_job_and_respects_retry_after(campaign_db: Engine) -> None:
    phone_subscribed(campaign_db)
    alert(campaign_db, "a1", "relance", DAY)
    client, seen = fake_client(lambda r: httpx.Response(429, headers={"Retry-After": "120"}))
    job = push_job(KEYS, campaign_db, client, PARIS)
    assert job is not None
    job(DAY)
    job(DAY + timedelta(seconds=60))  # en pause : rien n'est demandé
    assert len(seen.requests) == 1 and _pending(campaign_db) == 1
    job(DAY + timedelta(seconds=121))
    assert len(seen.requests) == 2
    assert push_job(None, campaign_db, client, PARIS) is None
