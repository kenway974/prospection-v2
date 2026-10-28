"""Alertes dans l'app (C78, C98, C108) ; envoyées aussi sur le téléphone au lot Web Push."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, func, select, update
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.schema_followup import alerts


@dataclass(frozen=True)
class Alert:
    id: int
    kind: str
    message: str
    link: str
    created_at: datetime


def add_alert(
    conn: Connection, key: str, kind: str, message: str, link: str, now: datetime
) -> bool:
    """Une seule alerte par clé (pas de doublon si la tâche de fond repasse). Vrai si neuve."""
    values = {"key": key, "kind": kind, "message": message[:300], "link": link, "created_at": now}
    statement = insert(alerts).values(**values).on_conflict_do_nothing(index_elements=["key"])
    return conn.execute(statement.returning(alerts.c.id)).first() is not None


def unseen_alerts(conn: Connection, limit: int = 20) -> list[Alert]:
    a = alerts.c
    rows = conn.execute(
        select(a.id, a.kind, a.message, a.link, a.created_at)
        .where(a.seen_at.is_(None)).order_by(a.created_at.desc(), a.id.desc()).limit(limit)
    )  # fmt: skip
    return [Alert(r.id, r.kind, r.message, r.link, r.created_at) for r in rows]


def unseen_count(conn: Connection) -> int:
    return int(conn.execute(select(func.count()).where(alerts.c.seen_at.is_(None))).scalar_one())


def mark_seen(conn: Connection, now: datetime, alert_id: int | None = None) -> None:
    """Une alerte, ou toutes si aucun identifiant."""
    query = update(alerts).where(alerts.c.seen_at.is_(None))
    if alert_id is not None:
        query = query.where(alerts.c.id == alert_id)
    conn.execute(query.values(seen_at=now))


def retire_alerts(conn: Connection, prefix: str, keep: set[str], now: datetime) -> None:
    """Marque vues les alertes non lues de ce type dont le sujet n'existe plus."""
    a = alerts.c
    query = update(alerts).where(a.seen_at.is_(None), a.key.startswith(prefix, autoescape=True))
    if keep:
        query = query.where(a.key.not_in(keep))
    conn.execute(query.values(seen_at=now))
