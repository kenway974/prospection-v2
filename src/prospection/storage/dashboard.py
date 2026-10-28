"""Chiffres des campagnes pour le tableau de bord (C80)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, func, select

from prospection.storage.schema_campaigns import campaigns

_C = campaigns.c


@dataclass(frozen=True)
class CampaignStats:
    id: int
    name: str
    created_at: datetime
    status: str
    found: int
    qualified: int
    cost_cents: int


def campaign_stats(conn: Connection, limit: int) -> list[CampaignStats]:
    rows = conn.execute(
        select(_C.id, _C.name, _C.created_at, _C.status, _C.found, _C.qualified, _C.cost_cents)
        .order_by(_C.created_at.desc(), _C.id.desc()).limit(limit)
    )  # fmt: skip
    return [CampaignStats(*r) for r in rows]


def totals(conn: Connection) -> tuple[int, int, int, int]:
    """Nombre de campagnes, trouvés, qualifiés, coût (centimes), sur toute la période."""
    row = conn.execute(
        select(func.count(), func.coalesce(func.sum(_C.found), 0),
               func.coalesce(func.sum(_C.qualified), 0), func.coalesce(func.sum(_C.cost_cents), 0))
    ).one()  # fmt: skip
    return int(row[0]), int(row[1]), int(row[2]), int(row[3])
