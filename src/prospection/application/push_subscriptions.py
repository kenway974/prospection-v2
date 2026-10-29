"""Abonnement d'un téléphone aux notifications : ce que le navigateur envoie, vérifié."""

from datetime import datetime
from typing import Any

from sqlalchemy import Engine

from prospection.domain.push_rules import allowed_endpoint
from prospection.storage import push as store

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
