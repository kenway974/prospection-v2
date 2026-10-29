"""Téléphones abonnés aux notifications et alertes à leur envoyer (Web Push)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Connection, delete, select, update
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.alerts import Alert
from prospection.storage.schema_followup import alerts, push_subscriptions

_S, _A = push_subscriptions.c, alerts.c
FRESH = timedelta(hours=24)  # au-delà, une alerte n'est plus envoyée (elle reste dans l'app)


@dataclass(frozen=True)
class Subscription:
    endpoint: str
    p256dh: str
    auth: str


def save_subscription(conn: Connection, sub: Subscription, now: datetime) -> None:
    values = {"endpoint": sub.endpoint, "p256dh": sub.p256dh, "auth": sub.auth}
    statement = insert(push_subscriptions).values(**values, created_at=now)
    conn.execute(statement.on_conflict_do_update(index_elements=["endpoint"], set_=values))


def delete_subscription(conn: Connection, endpoint: str) -> None:
    conn.execute(delete(push_subscriptions).where(_S.endpoint == endpoint))


def subscriptions(conn: Connection) -> list[Subscription]:
    rows = conn.execute(select(_S.endpoint, _S.p256dh, _S.auth).order_by(_S.id))
    return [Subscription(*r) for r in rows]


def take_alerts(
    conn: Connection, now: datetime, only: frozenset[str] | None, limit: int = 20
) -> list[Alert]:
    """Pas encore envoyées, pas encore vues, récentes (`only` : ces sortes seulement) ;
    marquées envoyées aussitôt : deux workers n'envoient jamais la même deux fois."""
    query = select(_A.id).where(
        _A.pushed_at.is_(None), _A.seen_at.is_(None), _A.created_at > now - FRESH
    )
    if only is not None:
        query = query.where(_A.kind.in_(only))
    chosen = query.order_by(_A.created_at, _A.id).limit(limit).with_for_update(skip_locked=True)
    rows = conn.execute(
        update(alerts).where(_A.id.in_(chosen.scalar_subquery())).values(pushed_at=now)
        .returning(_A.id, _A.kind, _A.message, _A.link, _A.created_at)
    )  # fmt: skip
    return sorted((Alert(*r) for r in rows), key=lambda a: (a.created_at, a.id))


def give_back(conn: Connection, alert_ids: list[int]) -> None:
    """Envoi raté (service injoignable) : l'alerte repartira au prochain passage."""
    if alert_ids:
        conn.execute(update(alerts).where(_A.id.in_(alert_ids)).values(pushed_at=None))
