"""Mise à jour des fiches d'une campagne passée (C76) : file des prospects à relire."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Connection, func, select, update

from prospection.storage.schema_calls import prospect_actions
from prospection.storage.schema_campaigns import campaigns, prospects

_P, _C = prospects.c, campaigns.c
STALE = timedelta(minutes=10)  # fiche prise par un worker coupé : comptée comme finie


@dataclass(frozen=True)
class ToRefresh:
    prospect_id: int
    campaign_id: int
    place_id: str
    data: dict[str, Any]
    status: str | None


def _targets(campaign_id: int) -> list[Any]:
    return [_P.campaign_id == campaign_id, _P.qualified.is_(True),
            ~_P.place_id.startswith("siren:")]  # fmt: skip


def start_refresh(conn: Connection, campaign_id: int) -> int:
    """Met les fiches retenues en file, sauf si une mise à jour tourne déjà (pas de double
    paiement) ; renvoie leur nombre (0 si refusé)."""
    started = conn.execute(
        update(campaigns).where(_C.id == campaign_id, _C.status == "done",
                                _C.refresh_running.is_(False))
        .values(refresh_running=True).returning(_C.id)
    ).first()  # fmt: skip
    if started is None:
        return 0
    query = update(prospects).where(*_targets(campaign_id)).values(refresh_pending=True)
    return len(conn.execute(query.returning(_P.id)).all())


def refresh_state(conn: Connection, campaign_id: int) -> tuple[int, int, bool]:
    """Fiches à relire au total, encore en file, et si une mise à jour tourne."""
    total = conn.execute(select(func.count()).where(*_targets(campaign_id))).scalar_one()
    pending = conn.execute(
        select(func.count()).where(_P.campaign_id == campaign_id, _P.refresh_pending)
    ).scalar_one()
    running = conn.execute(select(_C.refresh_running).where(_C.id == campaign_id)).scalar_one()
    return int(total), int(pending), bool(running)


def take_refresh(conn: Connection, now: datetime) -> ToRefresh | None:
    """Prend un prospect de la file et l'en retire aussitôt : deux workers ne paient jamais
    deux fois la même fiche ; une coupure laisse seulement cette fiche non relue."""
    first = (
        select(_P.id).where(_P.refresh_pending).order_by(_P.id).limit(1)
        .with_for_update(skip_locked=True).scalar_subquery()
    )  # fmt: skip
    row = conn.execute(
        update(prospects).where(_P.id == first)
        .values(refresh_pending=False, refresh_taken_at=now)
        .returning(_P.id, _P.campaign_id, _P.place_id, _P.data_json, _P.status)
    ).first()  # fmt: skip
    if row is None:
        return None
    return ToRefresh(row.id, row.campaign_id, row.place_id, row.data_json, row.status)


def release(conn: Connection, prospect_id: int) -> None:
    conn.execute(update(prospects).where(_P.id == prospect_id).values(refresh_taken_at=None))


def cancel_refresh(conn: Connection, campaign_id: int) -> bool:
    """Arrête la mise à jour ; vrai si elle tournait encore."""
    query = update(prospects).where(_P.campaign_id == campaign_id, _P.refresh_pending)
    conn.execute(query.values(refresh_pending=False))
    return _close(conn, campaign_id)


def finish_refresh(conn: Connection, campaign_id: int, now: datetime) -> bool:
    """Vrai pour un seul worker, quand plus rien n'est en file ni en cours de lecture."""
    busy = conn.execute(
        select(func.count()).where(
            _P.campaign_id == campaign_id,
            _P.refresh_pending | (_P.refresh_taken_at > now - STALE),
        )
    ).scalar_one()
    return not busy and _close(conn, campaign_id)


def _close(conn: Connection, campaign_id: int) -> bool:
    query = update(campaigns).where(_C.id == campaign_id, _C.refresh_running.is_(True))
    return conn.execute(query.values(refresh_running=False).returning(_C.id)).first() is not None


def save_refresh(
    conn: Connection, item: ToRefresh, data: dict[str, Any], now: datetime, closed: str | None
) -> None:
    """Fiche relue ; `closed` : fermée pour de bon, elle sort de la liste à appeler, le
    compteur de la campagne baisse et ses actions ouvertes sont closes."""
    values: dict[str, Any] = {"data_json": data, "refresh_taken_at": None}
    if closed:
        values |= {"qualified": False, "status": None,
                   "reasons": func.array_append(_P.reasons, closed)}  # fmt: skip
        conn.execute(update(campaigns).where(_C.id == item.campaign_id)
                     .values(qualified=_C.qualified - 1))  # fmt: skip
        a = prospect_actions.c
        still_open = (a.prospect_id == item.prospect_id) & a.done_at.is_(None)
        conn.execute(update(prospect_actions).where(still_open).values(done_at=now))
    conn.execute(update(prospects).where(_P.id == item.prospect_id).values(**values))
