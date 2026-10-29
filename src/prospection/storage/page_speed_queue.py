"""File des sites à mesurer avec PageSpeed : prospects retenus dont le site est adopté."""

from datetime import datetime
from typing import Any

from sqlalchemy import Connection, literal, select, update
from sqlalchemy.dialects.postgresql import JSONB

from prospection.storage.schema_campaigns import prospects

_P = prospects.c


def take_site(conn: Connection, now: datetime) -> tuple[int, str] | None:
    """Un site pas encore mesuré, marqué aussitôt : jamais mesuré deux fois en même temps."""
    first = (
        select(_P.id)
        .where(_P.qualified.is_(True), _P.speed_checked_at.is_(None),
               _P.site_json["url"].astext.is_not(None))
        .order_by(_P.id).limit(1).with_for_update(skip_locked=True).scalar_subquery()
    )  # fmt: skip
    row = conn.execute(
        update(prospects).where(_P.id == first).values(speed_checked_at=now)
        .returning(_P.id, _P.site_json["url"].astext)
    ).first()  # fmt: skip
    return (int(row[0]), str(row[1])) if row else None


def save_speed(conn: Connection, prospect_id: int, speed: dict[str, Any]) -> None:
    merged = _P.site_json.op("||")(literal({"speed": speed}, JSONB))  # le reste du rapport gardé
    conn.execute(update(prospects).where(_P.id == prospect_id).values(site_json=merged))


def give_back(conn: Connection, prospect_id: int) -> None:
    """Google indisponible : le site sera mesuré plus tard."""
    query = update(prospects).where(_P.id == prospect_id).values(speed_checked_at=None)
    conn.execute(query)
