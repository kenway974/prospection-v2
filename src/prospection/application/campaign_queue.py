"""File des campagnes pour la tâche de fond (C40).

Une campagne est prise par un seul worker à la fois (`FOR UPDATE SKIP LOCKED`).
Le worker la « signe » à chaque étape (heartbeat) ; si la signature date de plus
de 2 minutes (redémarrage, déploiement), un autre worker la reprend.
"""

from datetime import datetime, timedelta

from sqlalchemy import Engine, or_, select, update

from prospection.storage.schema_campaigns import campaigns

STALE_AFTER = timedelta(minutes=2)


def claim_next(engine: Engine, now: datetime, stale_after: timedelta = STALE_AFTER) -> int | None:
    c = campaigns.c
    waiting = or_(c.retry_at.is_(None), c.retry_at <= now)
    abandoned = or_(c.heartbeat_at.is_(None), c.heartbeat_at < now - stale_after)
    query = (
        select(c.id, c.status)
        .where(
            waiting, or_(c.status == "queued", (c.status.in_(["running", "stopping"])) & abandoned)
        )
        .order_by(c.created_at, c.id)
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
            .values(status=status, heartbeat_at=now, retry_at=None)
        )  # fmt: skip
    return int(row.id)


def heartbeat(engine: Engine, campaign_id: int, now: datetime) -> None:
    with engine.begin() as conn:
        conn.execute(
            update(campaigns).where(campaigns.c.id == campaign_id).values(heartbeat_at=now)
        )


def release_until(engine: Engine, campaign_id: int, retry_at: datetime) -> None:
    """Rend la campagne à la file ; elle sera reprise à partir de `retry_at`."""
    with engine.begin() as conn:
        conn.execute(
            update(campaigns).where(campaigns.c.id == campaign_id)
            .values(retry_at=retry_at, heartbeat_at=None)
        )  # fmt: skip
