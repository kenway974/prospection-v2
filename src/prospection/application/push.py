"""Notifications sur le téléphone (Web Push) : chaque alerte de l'app part aussi sur les
téléphones abonnés, sauf pendant les heures calmes (les relances passent toujours)."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import Engine

from prospection.application.push_subscriptions import unsubscribe
from prospection.domain.push_rules import ALWAYS, notification_text, quiet, safe_link
from prospection.sources.web_push import (
    PushFailed,
    PushGone,
    PushRejected,
    VapidKeys,
    send_push,
)
from prospection.storage import push as store
from prospection.storage.alerts import Alert
from prospection.storage.app_settings import load_app_settings

logger = logging.getLogger(__name__)
MAX_PAUSE_SECONDS = 3600


def _payload(alert: Alert) -> bytes:
    data = {"title": "Prospection", "body": notification_text(alert.message),
            "url": safe_link(alert.link), "tag": f"alerte-{alert.id}"}  # fmt: skip
    return json.dumps(data, ensure_ascii=False).encode()


class PushPaused(Exception):
    """Service indisponible : le passage s'arrête, les alertes restantes attendent."""

    def __init__(self, retry_after: int | None) -> None:
        super().__init__("pause")
        self.retry_after = retry_after


def _send_all(
    engine: Engine, client: httpx.Client, keys: VapidKeys, subs: list[store.Subscription],
    payload: bytes, now: datetime, urgency: str,
) -> int:  # fmt: skip
    """Envoie à chaque téléphone ; renvoie combien l'ont reçue (ou l'ont refusée pour de
    bon). Abonnement expiré : oublié. Service indisponible : PushPaused, tout de suite."""
    reached = 0
    for sub in subs:
        try:
            send_push(client, sub.endpoint, sub.p256dh, sub.auth, payload, keys, now, urgency)
            reached += 1
        except PushGone:
            unsubscribe(engine, sub.endpoint)
        except PushRejected as error:
            logger.warning("Notification abandonnée : %s", error)
            reached += 1  # rien à gagner à la renvoyer
        except PushFailed as error:
            logger.warning("Notification non envoyée : %s", error)
            raise PushPaused(error.retry_after) from None
    return reached


def push_pending(
    engine: Engine, client: httpx.Client, keys: VapidKeys, now: datetime, timezone: str
) -> int:
    """Envoie les alertes en attente ; renvoie combien sont parties. Toute alerte prise et
    pas envoyée est rendue, quoi qu'il arrive (erreur imprévue comprise). Lève PushPaused si
    le service de notification est indisponible."""
    with engine.connect() as conn:
        settings, subs = load_app_settings(conn), store.subscriptions(conn)
    if not subs:
        return 0
    calm = quiet(now.astimezone(ZoneInfo(timezone)), settings.quiet_start, settings.quiet_end)
    with engine.begin() as conn:
        taken = store.take_alerts(conn, now, ALWAYS if calm else None)
    pending = [a.id for a in taken]
    try:
        for alert in taken:
            urgency = "high" if alert.kind in ALWAYS else "normal"
            if _send_all(engine, client, keys, subs, _payload(alert), now, urgency):
                pending.remove(alert.id)
            elif not _still_subscribed(engine):
                break  # plus aucun téléphone : les alertes attendent un abonnement
    finally:
        with engine.begin() as conn:
            store.give_back(conn, pending)
    return len(taken) - len(pending)


def _still_subscribed(engine: Engine) -> bool:
    with engine.connect() as conn:
        return bool(store.subscriptions(conn))


def send_test(engine: Engine, client: httpx.Client, keys: VapidKeys, now: datetime) -> int:
    """Notification d'essai ; renvoie le nombre de téléphones atteints."""
    with engine.connect() as conn:
        subs = store.subscriptions(conn)
    test = Alert(0, "essai", "Notification d'essai : tout fonctionne.", "/reglages/rappels", now)
    return _send_all(engine, client, keys, subs, _payload(test), now, "normal")


@dataclass
class _Backoff:
    until: datetime = field(default_factory=lambda: datetime.min.replace(tzinfo=UTC))
    misses: int = 0


def push_job(
    keys: VapidKeys | None, engine: Engine, client: httpx.Client, timezone: str
) -> Callable[[datetime], object] | None:
    """Travail régulier de la tâche de fond, si les clés VAPID sont configurées. Service
    indisponible : pause de plus en plus longue (Retry-After respecté), 1 h au plus."""
    if keys is None:
        return None
    configured, backoff = keys, _Backoff()

    def run(now: datetime) -> int:
        if now < backoff.until:
            return 0
        try:
            sent = push_pending(engine, client, configured, now, timezone)
        except PushPaused as paused:
            backoff.misses += 1
            wait = paused.retry_after or 30 * 2 ** min(backoff.misses, 7)
            backoff.until = now + timedelta(seconds=min(wait, MAX_PAUSE_SECONDS))
            return 0
        backoff.misses = 0
        return sent

    return run
