"""Origine et campagne des prospects listés : Terrain à part, filtre par campagne (C127, C128)."""

from sqlalchemy import ColumnElement, Connection, func, select

from prospection.domain.prospect_source import Scope
from prospection.storage.schema_campaigns import campaigns, prospects

_P, _C = prospects.c, campaigns.c


def scope_conditions(scope: Scope) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if scope.source:
        conditions.append(_P.campaign_id.in_(select(_C.id).where(_C.kind == scope.source)))
    if scope.campaign_id is not None:
        conditions.append(_P.campaign_id == scope.campaign_id)
    return conditions


def campaign_choices(conn: Connection, source: str) -> list[tuple[int, str, int]]:
    """Campagnes de cette origine qui ont des prospects retenus, les plus récentes d'abord."""
    rows = conn.execute(
        select(_C.id, _C.name, func.count(_P.id))
        .join(prospects, _P.campaign_id == _C.id)
        .where(_C.kind == source, _P.qualified.is_(True))
        .group_by(_C.id)
        .order_by(_C.created_at.desc(), _C.id.desc())
    )
    return [(int(i), str(name), int(n)) for i, name, n in rows]
