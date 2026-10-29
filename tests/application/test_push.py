"""Notifications sur le téléphone : chaque alerte part une fois, heures calmes respectées."""

import json
from datetime import UTC, datetime, timedelta

import http_ece
import httpx
import pytest
from sqlalchemy import Engine

from prospection.application.push import (
    InvalidSubscription,
    push_pending,
    send_test,
    subscribe,
)
from prospection.sources.web_push import VapidKeys, generate_vapid_keys
from prospection.storage.alerts import add_alert
from prospection.storage.push import subscriptions
from tests.fake_http import fake_client
from tests.sources.test_web_push import ENDPOINT, phone

PARIS = "Europe/Paris"
DAY = datetime(2026, 10, 29, 9, tzinfo=UTC)  # 10 h à Paris
NIGHT = datetime(2026, 10, 29, 22, tzinfo=UTC)  # 23 h à Paris
KEYS = VapidKeys(*generate_vapid_keys(), "mailto:moi@example.fr")


def phone_subscribed(engine: Engine) -> tuple[object, bytes]:
    receiver, p256dh, auth, secret = phone()
    subscribe(engine, {"endpoint": ENDPOINT, "keys": {"p256dh": p256dh, "auth": auth}}, DAY)
    return receiver, secret


def alert(engine: Engine, key: str, kind: str, at: datetime, link: str = "/prospects/1") -> None:
    with engine.begin() as conn:
        add_alert(conn, key, kind, f"{kind} · Boulangerie <b>Martin</b>", link, at)


def test_subscription_checked_field_by_field(campaign_db: Engine) -> None:
    refused: list[object] = [
        None, [], {"endpoint": "https://evil.fr/x", "keys": {"p256dh": "a", "auth": "b"}},
        {"endpoint": ENDPOINT, "keys": {"p256dh": "a b", "auth": "x"}}, {"endpoint": ENDPOINT},
    ]  # fmt: skip
    for bad in refused:
        with pytest.raises(InvalidSubscription):
            subscribe(campaign_db, bad, DAY)
    phone_subscribed(campaign_db)
    phone_subscribed(campaign_db)  # même téléphone : remplacé, pas doublé
    with campaign_db.connect() as conn:
        assert len(subscriptions(conn)) == 1


def test_each_alert_sent_once_to_the_phone(campaign_db: Engine) -> None:
    receiver, secret = phone_subscribed(campaign_db)
    alert(campaign_db, "a1", "nouveaux", DAY, link="https://evil.fr")
    client, seen = fake_client(lambda r: httpx.Response(201))
    assert push_pending(campaign_db, client, KEYS, DAY, PARIS) == 1
    assert push_pending(campaign_db, client, KEYS, DAY, PARIS) == 0  # jamais deux fois
    [sent] = seen.requests
    data = json.loads(http_ece.decrypt(sent.content, private_key=receiver, auth_secret=secret))
    assert data["body"] == "nouveaux · Boulangerie <b>Martin</b>" and data["url"] == "/"


def test_quiet_hours_let_only_follow_ups_through(campaign_db: Engine) -> None:
    phone_subscribed(campaign_db)
    alert(campaign_db, "n1", "nouveaux", NIGHT)
    alert(campaign_db, "r1", "relance", NIGHT)
    client, seen = fake_client(lambda r: httpx.Response(201))
    assert push_pending(campaign_db, client, KEYS, NIGHT, PARIS) == 1
    assert seen.requests[0].headers["Urgency"] == "high"
    morning = datetime(2026, 10, 30, 7, 5, tzinfo=UTC)  # 8 h 05 à Paris
    assert push_pending(campaign_db, client, KEYS, morning, PARIS) == 1  # la nouveauté attendait


def test_gone_phone_forgotten_busy_service_retried(campaign_db: Engine) -> None:
    phone_subscribed(campaign_db)
    alert(campaign_db, "a1", "echec", DAY)
    busy = fake_client(lambda r: httpx.Response(503))[0]
    assert push_pending(campaign_db, busy, KEYS, DAY, PARIS) == 0
    gone = fake_client(lambda r: httpx.Response(410))[0]
    assert push_pending(campaign_db, gone, KEYS, DAY + timedelta(minutes=1), PARIS) == 0
    with campaign_db.connect() as conn:
        assert subscriptions(conn) == []
    assert push_pending(campaign_db, busy, KEYS, DAY, PARIS) == 0  # plus de téléphone


def test_old_alerts_and_test_notification(campaign_db: Engine) -> None:
    client, seen = fake_client(lambda r: httpx.Response(201))
    assert send_test(campaign_db, client, KEYS, DAY) == 0  # aucun téléphone
    phone_subscribed(campaign_db)
    alert(campaign_db, "old", "nouveaux", DAY - timedelta(days=2))
    assert push_pending(campaign_db, client, KEYS, DAY, PARIS) == 0  # trop ancienne
    assert send_test(campaign_db, client, KEYS, DAY) == 1 and len(seen.requests) == 1
