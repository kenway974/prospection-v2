"""Notifications sur le téléphone (Web Push) : chaque alerte de l'app part aussi sur les
téléphones abonnés, sauf pendant les heures calmes (les relances passent toujours)."""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import Engine

from prospection.domain.push_rules import (
    ALWAYS,
    allowed_endpoint,
    notification_text,
    quiet,
    safe_link,
)
from prospection.sources.web_push import PushFailed, PushGone, VapidKeys, send_push
from prospection.storage import push as store
from prospection.storage.alerts import Alert
from prospection.storage.app_settings import load_app_settings

logger = logging.getLogger(__name__)
_KEY_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")


class InvalidSubscription(ValueError):
    """Abonnement refusé ; le message dit quoi faire."""


def _key(value: object) -> str:
    if not isinstance(value, str) or not 0 < len(value) <= 200 or set(value) - _KEY_CHARS:
        raise InvalidSubscription("Abonnement illisible : réessayez depuis Réglages → Rappels.")
    return value


def subscribe(engine: Engine, body: Any, now: datetime) -> None:
    """Ce que le navigateur envoie (`PushSubscription.toJSON()`), vérifié champ par champ."""
    endpoint = body.get("endpoint") if isinstance(body, dict) else None
    keys = body.get("keys") if isinstance(body, dict) else None
    if not isinstance(endpoint, str) or not allowed_endpoint(endpoint):
        raise InvalidSubscription("Navigateur non pris en charge pour les notifications.")
    if not isinstance(keys, dict):
        raise InvalidSubscription("Abonnement illisible : réessayez depuis Réglages → Rappels.")
    sub = store.Subscription(endpoint, _key(keys.get("p256dh")), _key(keys.get("auth")))
    with engine.begin() as conn:
        store.save_subscription(conn, sub, now)


def unsubscribe(engine: Engine, endpoint: str) -> None:
    with engine.begin() as conn:
        store.delete_subscription(conn, endpoint)


def _payload(alert: Alert) -> bytes:
    data = {"title": "Prospection", "body": notification_text(alert.message),
            "url": safe_link(alert.link), "tag": f"alerte-{alert.id}"}  # fmt: skip
    return json.dumps(data, ensure_ascii=False).encode()


def _send_all(
    engine: Engine, client: httpx.Client, keys: VapidKeys, subs: list[store.Subscription],
    payload: bytes, now: datetime, urgency: str,
) -> int:  # fmt: skip
    """Envoie à chaque téléphone ; renvoie combien l'ont reçue. Abonnement expiré : oublié."""
    reached = 0
    for sub in subs:
        try:
            send_push(client, sub.endpoint, sub.p256dh, sub.auth, payload, keys, now, urgency)
            reached += 1
        except PushGone:
            unsubscribe(engine, sub.endpoint)
        except PushFailed as error:
            logger.warning("Notification non envoyée : %s", error)
    return reached


def push_pending(
    engine: Engine, client: httpx.Client, keys: VapidKeys, now: datetime, timezone: str
) -> int:
    """Envoie les alertes en attente ; renvoie combien sont parties."""
    with engine.connect() as conn:
        settings, subs = load_app_settings(conn), store.subscriptions(conn)
    if not subs:
        return 0
    calm = quiet(now.astimezone(ZoneInfo(timezone)), settings.quiet_start, settings.quiet_end)
    with engine.begin() as conn:
        taken = store.take_alerts(conn, now, ALWAYS if calm else None)
    failed = []
    for alert in taken:
        urgency = "high" if alert.kind in ALWAYS else "normal"
        if not _send_all(engine, client, keys, subs, _payload(alert), now, urgency):
            failed.append(alert.id)
    with engine.begin() as conn:
        store.give_back(conn, failed)
    return len(taken) - len(failed)


def send_test(engine: Engine, client: httpx.Client, keys: VapidKeys, now: datetime) -> int:
    """Notification d'essai ; renvoie le nombre de téléphones atteints."""
    with engine.connect() as conn:
        subs = store.subscriptions(conn)
    test = Alert(0, "essai", "Notification d'essai : tout fonctionne.", "/reglages/rappels", now)
    return _send_all(engine, client, keys, subs, _payload(test), now, "normal")


def push_job(
    keys: VapidKeys | None, engine: Engine, client: httpx.Client, timezone: str
) -> Callable[[datetime], object] | None:
    """Travail régulier de la tâche de fond, si les clés VAPID sont configurées."""
    if keys is None:
        return None
    configured = keys
    return lambda now: push_pending(engine, client, configured, now, timezone)
