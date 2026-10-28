"""RGPD : purge des prospects non retenus (C94) et suppression d'une entreprise (C95)."""

from datetime import datetime

from sqlalchemy import Connection, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from prospection.domain.privacy import PURGEABLE, erasure_key
from prospection.storage.schema_calls import prospect_actions, prospect_notes
from prospection.storage.schema_campaigns import campaign_events, exclusion_names, prospects
from prospection.storage.schema_followup import alerts

ERASED = "erased"
_P = prospects.c


def _forget(conn: Connection, rows: list[tuple[int, str]]) -> None:
    """Alertes et lignes de journal qui citent ces prospects (nom, lien)."""
    if not rows:
        return
    links = [f"/prospects/{pid}" for pid, _ in rows]
    conn.execute(delete(alerts).where(alerts.c.link.in_(links)))
    e = campaign_events.c
    names = {name for _, name in rows if name}
    for name in names:
        conn.execute(
            delete(campaign_events).where(e.message.startswith(f"{name} : ", autoescape=True))
        )


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
        ).returning(_P.id, _P.data_json["name"].astext)
    ).all()  # fmt: skip
    _forget(conn, [(r[0], r[1]) for r in rows])
    conn.execute(delete(alerts).where(alerts.c.created_at < cutoff))
    return len(rows)


def erase_company(conn: Connection, prospect_id: int) -> int:
    """Toutes les fiches de l'entreprise (même fiche Google ou même SIREN), dans toutes les
    campagnes, puis une empreinte pour ne plus jamais la reprendre. Renvoie combien."""
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
    rows = conn.execute(
        delete(prospects).where(or_(*same)).returning(_P.id, _P.data_json["name"].astext)
    ).all()
    _forget(conn, [(r[0], r[1]) for r in rows])
    values = [{"kind": ERASED, "name_norm": key, "name": "(entreprise supprimée)"} for key in keys]
    conn.execute(insert(exclusion_names).values(values).on_conflict_do_nothing())
    return len(rows)


def erased_keys(conn: Connection) -> frozenset[str]:
    e = exclusion_names.c
    return frozenset(conn.scalars(select(e.name_norm).where(e.kind == ERASED)))
