"""Campagnes et leur journal (C34, C35, C37, C79)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, insert, select, update

from prospection.domain.campaign_request import CampaignRequest
from prospection.storage.campaign_codec import decode_request, encode_circle, encode_request
from prospection.storage.campaign_steps import StepSpec
from prospection.storage.schema_campaigns import campaign_events, campaign_steps, campaigns


@dataclass(frozen=True)
class Campaign:
    id: int
    request: CampaignRequest
    status: str
    stop_reason: str | None
    found: int
    excluded: int
    qualified: int
    cost_cents: int


@dataclass(frozen=True)
class Event:
    at: datetime
    level: str
    message: str


def create_campaign(
    conn: Connection, request: CampaignRequest, steps: Sequence[StepSpec], now: datetime
) -> int:
    values = {"name": request.name, "request_json": encode_request(request), "status": "queued"}
    counters = {"found": 0, "excluded": 0, "qualified": 0, "cost_cents": 0}
    campaign_id = int(
        conn.execute(
            insert(campaigns)
            .values(**values, **counters, created_at=now, updated_at=now)
            .returning(campaigns.c.id)
        ).scalar_one()
    )
    rows = [
        {"campaign_id": campaign_id, "position": i, "query": s.query, "keyword": s.keyword,
         "zone_label": s.zone_label, "bias": encode_circle(s.bias),
         "restrict_to_bias": s.restrict_to_bias, "department": s.department,
         "page_number": 0, "done": False, "attempts": 0}
        for i, s in enumerate(steps)
    ]  # fmt: skip
    if rows:
        conn.execute(insert(campaign_steps), rows)
    return campaign_id


def load_campaign(conn: Connection, campaign_id: int) -> Campaign:
    row = conn.execute(select(campaigns).where(campaigns.c.id == campaign_id)).one()
    return Campaign(
        row.id, decode_request(row.request_json), row.status, row.stop_reason,
        row.found, row.excluded, row.qualified, row.cost_cents,
    )  # fmt: skip


def set_status(
    conn: Connection, campaign_id: int, status: str, now: datetime, reason: str | None = None,
    only_from: tuple[str, ...] | None = None,
) -> bool:  # fmt: skip
    """Vrai si l'état a changé ; `only_from` : seulement depuis ces états (pas de course)."""
    values: dict[str, object] = {"status": status, "updated_at": now}
    if reason is not None:
        values["stop_reason"] = reason
    query = update(campaigns).where(campaigns.c.id == campaign_id)
    if only_from is not None:
        query = query.where(campaigns.c.status.in_(only_from))
    return conn.execute(query.values(**values).returning(campaigns.c.id)).first() is not None


def add_counts(
    conn: Connection, campaign_id: int, now: datetime, found: int, excluded: int,
    qualified: int, cost_cents: int,
) -> None:  # fmt: skip
    c = campaigns.c
    conn.execute(
        update(campaigns).where(c.id == campaign_id).values(
            found=c.found + found, excluded=c.excluded + excluded,
            qualified=c.qualified + qualified, cost_cents=c.cost_cents + cost_cents,
            updated_at=now,
        )
    )  # fmt: skip


def add_event(conn: Connection, campaign_id: int, at: datetime, level: str, message: str) -> None:
    values = {"campaign_id": campaign_id, "at": at, "level": level, "message": message[:300]}
    conn.execute(insert(campaign_events).values(**values))


def recent_events(conn: Connection, campaign_id: int, limit: int) -> list[Event]:
    e = campaign_events.c
    rows = conn.execute(
        select(e.at, e.level, e.message).where(e.campaign_id == campaign_id)
        .order_by(e.at.desc(), e.id.desc()).limit(limit)
    )  # fmt: skip
    return [Event(r.at, r.level, r.message) for r in rows]


def recent_campaigns(conn: Connection, limit: int) -> list[Campaign]:
    query = select(campaigns.c.id).order_by(campaigns.c.created_at.desc()).limit(limit)
    return [load_campaign(conn, campaign_id) for campaign_id in conn.scalars(query)]
