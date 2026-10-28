"""Mise à jour des fiches d'une campagne passée (C76) : file des prospects à relire."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, func, select, update

from prospection.storage.schema_campaigns import prospects

_P = prospects.c


@dataclass(frozen=True)
class ToRefresh:
    prospect_id: int
    campaign_id: int
    place_id: str
    data: dict[str, Any]
    status: str | None


def queue_refresh(conn: Connection, campaign_id: int) -> int:
    """Les prospects retenus de la campagne (fiches Google) ; renvoie leur nombre."""
    query = (
        update(prospects)
        .where(_P.campaign_id == campaign_id, _P.qualified.is_(True),
               ~_P.place_id.startswith("siren:"))
        .values(refresh_pending=True).returning(_P.id)
    )  # fmt: skip
    return len(conn.execute(query).all())


def refresh_targets(conn: Connection, campaign_id: int) -> int:
    query = select(func.count()).where(
        _P.campaign_id == campaign_id, _P.qualified.is_(True), ~_P.place_id.startswith("siren:")
    )
    return int(conn.execute(query).scalar_one())


def pending_refresh(conn: Connection, campaign_id: int) -> int:
    query = select(func.count()).where(_P.campaign_id == campaign_id, _P.refresh_pending)
    return int(conn.execute(query).scalar_one())


def take_refresh(conn: Connection) -> ToRefresh | None:
    """Prend un prospect de la file et l'en retire aussitôt : deux workers ne paient jamais
    deux fois la même fiche ; une coupure laisse seulement cette fiche non relue."""
    first = (
        select(_P.id).where(_P.refresh_pending).order_by(_P.id).limit(1)
        .with_for_update(skip_locked=True).scalar_subquery()
    )  # fmt: skip
    row = conn.execute(
        update(prospects).where(_P.id == first).values(refresh_pending=False)
        .returning(_P.id, _P.campaign_id, _P.place_id, _P.data_json, _P.status)
    ).first()  # fmt: skip
    if row is None:
        return None
    return ToRefresh(row.id, row.campaign_id, row.place_id, row.data_json, row.status)


def cancel_refresh(conn: Connection, campaign_id: int) -> None:
    query = update(prospects).where(_P.campaign_id == campaign_id, _P.refresh_pending)
    conn.execute(query.values(refresh_pending=False))


def save_refresh(
    conn: Connection, prospect_id: int, data: dict[str, Any], exclude: str | None = None
) -> None:
    """Fiche relue ; `exclude` : retirée de la liste à appeler (fermée définitivement)."""
    values: dict[str, Any] = {"data_json": data}
    if exclude:
        values |= {"qualified": False, "status": None,
                   "reasons": func.array_append(_P.reasons, exclude)}  # fmt: skip
    conn.execute(update(prospects).where(_P.id == prospect_id).values(**values))
