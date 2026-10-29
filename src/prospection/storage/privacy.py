"""RGPD : purge des prospects non retenus (C94), suppression d'une entreprise (C95) ou d'une
sélection de prospects (C129)."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from prospection.domain.privacy import PURGEABLE, erasure_key
from prospection.domain.trades import normalize
from prospection.storage.schema_calls import prospect_actions, prospect_notes
from prospection.storage.schema_campaigns import campaign_events, exclusion_names, prospects
from prospection.storage.schema_followup import alerts

ERASED, BLACKLIST = "erased", "blacklist"
_P = prospects.c
_DELETED = (_P.id, _P.data_json["name"].astext, _P.campaign_id)


def _forget(conn: Connection, rows: Sequence[Any]) -> None:
    """Alertes et lignes de journal (de leurs campagnes seulement) qui citent ces prospects."""
    if not rows:
        return
    links = [f"/prospects/{r[0]}" for r in rows]
    conn.execute(delete(alerts).where(alerts.c.link.in_(links)))
    e = campaign_events.c
    for name, campaign_id in {(r[1], r[2]) for r in rows if r[1]}:
        named = e.message.startswith(f"{name} : ", autoescape=True)
        conn.execute(delete(campaign_events).where(e.campaign_id == campaign_id, named))


def purge_inactive(conn: Connection, cutoff: datetime) -> int:
    """Non retenus sans activité depuis `cutoff` ; jamais un prospect avec une action
    ouverte. Activité : création, changement, note, action. Renvoie combien sont supprimés."""
    n, a = prospect_notes.c, prospect_actions.c
    last_note = select(func.max(n.created_at)).where(n.prospect_id == _P.id).scalar_subquery()
    last_action = (
        select(func.max(func.greatest(a.created_at, a.done_at)))
        .where(a.prospect_id == _P.id).scalar_subquery()
    )  # fmt: skip
    open_action = select(a.id).where(a.prospect_id == _P.id, a.done_at.is_(None)).exists()
    activity = func.greatest(_P.created_at, _P.updated_at, last_note, last_action)
    rows = conn.execute(
        delete(prospects).where(
            or_(_P.qualified.is_(False), _P.status.in_(PURGEABLE)), activity < cutoff,
            ~open_action,
        ).returning(*_DELETED)
    ).all()  # fmt: skip
    _forget(conn, rows)
    conn.execute(delete(alerts).where(alerts.c.created_at < cutoff))
    return len(rows)


def erase_company(conn: Connection, prospect_id: int, keep_blacklist: bool = False) -> int:
    """Toutes les fiches de l'entreprise (même fiche Google ou même SIREN), dans toutes les
    campagnes, son entrée de liste noire (sauf si je la garde), puis une empreinte pour ne
    plus jamais la reprendre. Renvoie combien de fiches."""
    row = conn.execute(
        select(_P.place_id, _P.company_json["siren"].astext).where(_P.id == prospect_id)
    ).first()
    if row is None:
        return 0
    place_id, siren = row[0], row[1]
    same = [_P.place_id == place_id]
    keys = {erasure_key(place_id)}
    if siren:
        same += [_P.company_json["siren"].astext == siren, _P.place_id == f"siren:{siren}"]
        keys.add(erasure_key(f"siren:{siren}"))
    rows = conn.execute(delete(prospects).where(or_(*same)).returning(*_DELETED)).all()
    _forget(conn, rows)
    names = {normalize(r[1]) for r in rows if r[1]}
    if names and not keep_blacklist:
        e = exclusion_names.c
        conn.execute(delete(exclusion_names).where(e.kind == BLACKLIST, e.name_norm.in_(names)))
    values = [{"kind": ERASED, "name_norm": key, "name": "(entreprise supprimée)"} for key in keys]
    conn.execute(insert(exclusion_names).values(values).on_conflict_do_nothing())
    return len(rows)


def prospect_names(conn: Connection, prospect_ids: Sequence[int]) -> list[tuple[int, str]]:
    """Prospects retenus qui existent encore parmi ces identifiants, dans l'ordre de la liste."""
    rows = conn.execute(
        select(_P.id, _P.data_json["name"].astext)
        .where(_P.id.in_(prospect_ids), _P.qualified.is_(True)).order_by(_P.created_at, _P.id)
    )  # fmt: skip
    return [(int(i), name or "Sans nom") for i, name in rows]


def delete_prospects(conn: Connection, prospect_ids: Sequence[int]) -> int:
    """Ces prospects, leurs notes, actions et alertes ; une recherche pourra les reprendre."""
    rows = conn.execute(delete(prospects).where(_P.id.in_(prospect_ids)).returning(*_DELETED)).all()
    _forget(conn, rows)
    return len(rows)


def erased_keys(conn: Connection) -> frozenset[str]:
    e = exclusion_names.c
    return frozenset(conn.scalars(select(e.name_norm).where(e.kind == ERASED)))
