"""File des pages Google à lire pour une campagne (C40 : reprise là où on s'était arrêté)."""

from dataclasses import dataclass

from sqlalchemy import Connection, select, update

from prospection.domain.google_cost import MAX_PAGES_PER_QUERY
from prospection.domain.place import Circle
from prospection.storage.campaign_codec import decode_circle
from prospection.storage.schema_campaigns import campaign_steps


@dataclass(frozen=True)
class StepSpec:
    query: str
    keyword: str
    zone_label: str
    bias: Circle | None
    restrict_to_bias: bool = False


@dataclass(frozen=True)
class Step:
    id: int
    query: str
    keyword: str
    zone_label: str
    bias: Circle | None
    restrict_to_bias: bool
    page_token: str | None
    page_number: int
    attempts: int


def next_step(conn: Connection, campaign_id: int) -> Step | None:
    s = campaign_steps.c
    row = conn.execute(
        select(campaign_steps)
        .where(s.campaign_id == campaign_id, s.done.is_(False))
        .order_by(s.position)
        .limit(1)
    ).first()
    if row is None:
        return None
    return Step(
        row.id, row.query, row.keyword, row.zone_label, decode_circle(row.bias),
        row.restrict_to_bias,
        row.page_token, row.page_number, row.attempts,
    )  # fmt: skip


def record_page(conn: Connection, step_id: int, next_token: str | None) -> None:
    """Page lue : on passe à la suivante, ou l'étape est finie (plus de page ou 3 lues)."""
    s = campaign_steps.c
    row = conn.execute(select(s.page_number).where(s.id == step_id)).one()
    number = row.page_number + 1
    done = next_token is None or number >= MAX_PAGES_PER_QUERY
    conn.execute(
        update(campaign_steps).where(s.id == step_id).values(
            page_token=next_token, page_number=number, done=done, attempts=0
        )
    )  # fmt: skip


def skip_step(conn: Connection, step_id: int) -> None:
    conn.execute(update(campaign_steps).where(campaign_steps.c.id == step_id).values(done=True))


def count_attempt(conn: Connection, step_id: int) -> int:
    s = campaign_steps.c
    return int(
        conn.execute(
            update(campaign_steps).where(s.id == step_id)
            .values(attempts=s.attempts + 1).returning(s.attempts)
        ).scalar_one()
    )  # fmt: skip
