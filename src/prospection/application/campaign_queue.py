"""File des campagnes pour la tâche de fond (C40).

Une campagne est prise par un seul worker à la fois (`FOR UPDATE SKIP LOCKED`),
pour une page, puis rendue à la file : les campagnes avancent à tour de rôle.
Si elle n'est pas rendue dans les 10 minutes (redémarrage, worker figé), un autre
worker la reprend ; l'ancien ne peut plus la rendre, elle n'est plus à lui.
"""

from datetime import datetime, timedelta

from sqlalchemy import Engine, func, or_, select, update

from prospection.storage.schema_campaigns import campaigns

STALE_AFTER = timedelta(minutes=10)  # une page lit aussi des sites : jusqu'à ~2 min


def claim_next(
    engine: Engine, now: datetime, worker_id: str, stale_after: timedelta = STALE_AFTER
) -> int | None:
    c = campaigns.c
    waiting = or_(c.retry_at.is_(None), c.retry_at <= now)
    abandoned = or_(c.heartbeat_at.is_(None), c.heartbeat_at < now - stale_after)
    query = (
        select(c.id, c.status)
        .where(
            waiting, or_(c.status == "queued", (c.status.in_(["running", "stopping"])) & abandoned)
        )
        .order_by(func.coalesce(c.retry_at, c.created_at), c.id)  # la plus en attente d'abord
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    with engine.begin() as conn:
        row = conn.execute(query).first()
        if row is None:
            return None
        status = "stopping" if row.status == "stopping" else "running"
        conn.execute(
            update(campaigns).where(c.id == row.id)
            .values(status=status, claimed_by=worker_id, heartbeat_at=now, retry_at=None)
        )  # fmt: skip
    return int(row.id)


def release_until(engine: Engine, campaign_id: int, retry_at: datetime, worker_id: str) -> None:
    """Rend la campagne à la file (reprise à partir de `retry_at`), seulement si ce worker
    la tient encore : un worker figé puis réveillé ne lâche pas celle d'un autre."""
    c = campaigns.c
    with engine.begin() as conn:
        conn.execute(
            update(campaigns).where(c.id == campaign_id, c.claimed_by == worker_id)
            .values(retry_at=retry_at, heartbeat_at=None, claimed_by=None)
        )  # fmt: skip
