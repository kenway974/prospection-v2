"""File des sites à mesurer avec PageSpeed : prospects retenus dont le site est adopté (un
site « probable », homonyme possible, n'a pas d'adresse adoptée : jamais mesuré)."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Connection, literal, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB

from prospection.storage.schema_campaigns import prospects

_P = prospects.c
STALE = timedelta(minutes=15)  # pris mais pas mesuré (worker coupé, erreur) : repris
MAX_ATTEMPTS = 3  # au-delà, le site est abandonné : il ne bloque jamais la file
REUSE = timedelta(days=30)  # même site déjà mesuré : la mesure est reprise, pas refaite


def take_site(conn: Connection, now: datetime) -> tuple[int, str] | None:
    """Un site à mesurer, marqué aussitôt (jamais deux fois en même temps) ; les plus
    anciens essais d'abord, un site en échec repasse en fin de file."""
    url = _P.site_json["url"].astext
    first = (
        select(_P.id)
        .where(_P.qualified.is_(True), url.is_not(None), _P.site_json["speed"].astext.is_(None),
               _P.speed_attempts < MAX_ATTEMPTS,
               or_(_P.speed_checked_at.is_(None), _P.speed_checked_at < now - STALE))
        .order_by(_P.speed_checked_at.asc().nulls_first(), _P.id)
        .limit(1).with_for_update(skip_locked=True).scalar_subquery()
    )  # fmt: skip
    row = conn.execute(
        update(prospects).where(_P.id == first)
        .values(speed_checked_at=now, speed_attempts=_P.speed_attempts + 1)
        .returning(_P.id, url)
    ).first()  # fmt: skip
    return (int(row[0]), str(row[1])) if row else None


def known_speed(conn: Connection, url: str, now: datetime) -> dict[str, Any] | None:
    """Mesure récente du même site sur un autre prospect (autre campagne…)."""
    query = select(_P.site_json["speed"]).where(
        _P.site_json["url"].astext == url, _P.site_json["speed"].astext.is_not(None),
        _P.speed_checked_at > now - REUSE,
    ).limit(1)  # fmt: skip
    value = conn.execute(query).scalar_one_or_none()
    return value if isinstance(value, dict) else None


def save_speed(conn: Connection, prospect_id: int, speed: dict[str, Any]) -> None:
    merged = _P.site_json.op("||")(literal({"speed": speed}, JSONB))  # le reste du rapport gardé
    conn.execute(update(prospects).where(_P.id == prospect_id).values(site_json=merged))


def not_its_fault(conn: Connection, prospect_id: int) -> None:
    """Clé refusée : l'essai ne compte pas contre ce site, il sera repris plus tard."""
    conn.execute(update(prospects).where(_P.id == prospect_id)
                 .values(speed_attempts=_P.speed_attempts - 1))  # fmt: skip
