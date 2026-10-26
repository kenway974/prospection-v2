"""Statut, notes, prochaine action et contact d'un prospect (C102 à C105)."""

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import Connection, select, update
from sqlalchemy.dialects.postgresql import insert

from prospection.domain.agenda import AgendaItem
from prospection.storage.schema_calls import prospect_actions, prospect_notes
from prospection.storage.schema_campaigns import prospects


@dataclass(frozen=True)
class Note:
    text: str
    created_at: datetime


@dataclass(frozen=True)
class Action:
    id: int
    kind: str
    due_date: date
    due_time: time | None


def set_call_status(conn: Connection, prospect_id: int, status: str, now: datetime) -> None:
    p = prospects.c
    conn.execute(update(prospects).where(p.id == prospect_id).values(status=status, updated_at=now))


def add_note(conn: Connection, prospect_id: int, text: str, now: datetime) -> None:
    conn.execute(insert(prospect_notes).values(prospect_id=prospect_id, text=text, created_at=now))


def notes(conn: Connection, prospect_id: int) -> list[Note]:
    n = prospect_notes.c
    rows = conn.execute(
        select(n.text, n.created_at).where(n.prospect_id == prospect_id)
        .order_by(n.created_at.desc(), n.id.desc())
    )  # fmt: skip
    return [Note(r.text, r.created_at) for r in rows]


def open_action(conn: Connection, prospect_id: int) -> Action | None:
    a = prospect_actions.c
    row = conn.execute(
        select(a.id, a.kind, a.due_date, a.due_time)
        .where(a.prospect_id == prospect_id, a.done_at.is_(None))
    ).first()  # fmt: skip
    return Action(row.id, row.kind, row.due_date, row.due_time) if row else None


def plan_action(
    conn: Connection, prospect_id: int, kind: str, due: date, at: time | None, now: datetime
) -> None:
    """Une seule action ouverte : la nouvelle remplace celle qui était prévue (sans course)."""
    values = {"kind": kind, "due_date": due, "due_time": at}
    statement = insert(prospect_actions).values(prospect_id=prospect_id, created_at=now, **values)
    conn.execute(
        statement.on_conflict_do_update(
            index_elements=["prospect_id"], index_where=prospect_actions.c.done_at.is_(None),
            set_=values,
        )
    )  # fmt: skip


def complete_action(conn: Connection, action_id: int, now: datetime) -> bool:
    a = prospect_actions.c
    done = conn.execute(
        update(prospect_actions).where(a.id == action_id, a.done_at.is_(None))
        .values(done_at=now).returning(a.id)
    ).first()  # fmt: skip
    return done is not None


def reopen_action(conn: Connection, action_id: int) -> bool:
    """Seulement si le prospect n'a pas déjà une autre action ouverte."""
    a = prospect_actions.c
    other = prospect_actions.alias("other")
    busy = select(other.c.id).where(
        other.c.prospect_id == a.prospect_id, other.c.done_at.is_(None)
    ).exists()  # fmt: skip
    reopened = conn.execute(
        update(prospect_actions).where(a.id == action_id, a.done_at.is_not(None), ~busy)
        .values(done_at=None).returning(a.id)
    ).first()  # fmt: skip
    return reopened is not None


def agenda_items(conn: Connection) -> list[AgendaItem]:
    """Actions ouvertes, avec le nom du prospect."""
    a, p = prospect_actions.c, prospects.c
    rows = conn.execute(
        select(a.id, a.prospect_id, p.data_json["name"].astext.label("name"), a.kind,
               a.due_date, a.due_time)
        .join(prospects, p.id == a.prospect_id).where(a.done_at.is_(None))
    )  # fmt: skip
    return [AgendaItem(r.id, r.prospect_id, r.name, r.kind, r.due_date, r.due_time) for r in rows]


def update_contact(
    conn: Connection, prospect_id: int, contact: tuple[str | None, str | None, str | None],
    now: datetime,
) -> None:  # fmt: skip
    name, mobile, email = contact
    conn.execute(
        update(prospects)
        .where(prospects.c.id == prospect_id)
        .values(contact_name=name, contact_mobile=mobile, contact_email=email, updated_at=now)
    )
