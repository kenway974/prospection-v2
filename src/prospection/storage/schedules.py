"""Campagnes programmées chaque semaine (C77)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, delete, select, update
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.schema_followup import campaign_schedules


@dataclass(frozen=True)
class Schedule:
    id: int
    template_name: str
    weekday: int
    hour: int
    next_run_at: datetime


def _schedule(r: Any) -> Schedule:
    return Schedule(r.id, r.template_name, r.weekday, r.hour, r.next_run_at)


def add_schedule(
    conn: Connection, template_name: str, weekday: int, hour: int, next_run_at: datetime,
    now: datetime,
) -> None:  # fmt: skip
    """Rien si la même programmation existe déjà (double appui)."""
    values = {"template_name": template_name, "weekday": weekday, "hour": hour,
              "next_run_at": next_run_at, "created_at": now}  # fmt: skip
    statement = (
        insert(campaign_schedules).values(**values).on_conflict_do_nothing(constraint="uq_schedule")
    )
    conn.execute(statement)


def list_schedules(conn: Connection) -> list[Schedule]:
    s = campaign_schedules.c
    return [_schedule(r) for r in conn.execute(select(campaign_schedules).order_by(s.id))]


def delete_schedule(conn: Connection, schedule_id: int) -> None:
    conn.execute(delete(campaign_schedules).where(campaign_schedules.c.id == schedule_id))


def claim_due(conn: Connection, now: datetime) -> Schedule | None:
    """La plus en retard des programmations échues, verrouillée (deux workers : une seule fois)."""
    s = campaign_schedules.c
    row = conn.execute(
        select(campaign_schedules).where(s.next_run_at <= now)
        .order_by(s.next_run_at).limit(1).with_for_update(skip_locked=True)
    ).first()  # fmt: skip
    return _schedule(row) if row else None


def set_next_run(conn: Connection, schedule_id: int, at: datetime) -> None:
    s = campaign_schedules.c
    conn.execute(update(campaign_schedules).where(s.id == schedule_id).values(next_run_at=at))
