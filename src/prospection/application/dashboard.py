"""Tableau de bord (C80) et journal complet d'une campagne (C81)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine

from prospection.domain.dashboard import cost_per_qualified, qualification_rate
from prospection.storage.campaigns import Event, recent_events
from prospection.storage.dashboard import CampaignStats, campaign_stats, totals
from prospection.storage.maintenance import last_backup

JOURNAL_SIZE = 500


@dataclass(frozen=True)
class Line:
    stats: CampaignStats
    rate: int | None
    cost_per_qualified: int | None


@dataclass(frozen=True)
class Dashboard:
    campaigns: int
    found: int
    qualified: int
    cost_cents: int
    rate: int | None
    cost_per_qualified: int | None
    lines: list[Line]


def dashboard(engine: Engine, limit: int = 30) -> Dashboard:
    with engine.connect() as conn:
        count, found, qualified, cost = totals(conn)
        stats = campaign_stats(conn, limit)
    lines = [Line(s, qualification_rate(s.found, s.qualified),
                  cost_per_qualified(s.cost_cents, s.qualified)) for s in stats]  # fmt: skip
    return Dashboard(count, found, qualified, cost, qualification_rate(found, qualified),
                     cost_per_qualified(cost, qualified), lines)  # fmt: skip


def backup_status(engine: Engine) -> tuple[datetime | None, str | None]:
    """Dernière sauvegarde réussie et dernière erreur (C91)."""
    with engine.connect() as conn:
        return last_backup(conn)


def journal(engine: Engine, campaign_id: int) -> list[Event]:
    """Tout ce qui a été fait, erreurs comprises, du plus récent au plus ancien."""
    with engine.connect() as conn:
        return recent_events(conn, campaign_id, JOURNAL_SIZE)
