"""Écran Aujourd'hui : actions en retard, du jour et de demain (C107).

Fonction pure : le « maintenant » et le fuseau sont passés en paramètres.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class AgendaItem:
    id: int
    prospect_id: int
    prospect_name: str
    kind: str
    due_date: date
    due_time: time | None


@dataclass(frozen=True)
class Agenda:
    overdue: list[AgendaItem]
    today: list[AgendaItem]
    tomorrow: list[AgendaItem]


def _order(item: AgendaItem) -> tuple[date, bool, time, str]:
    """Par date, puis les actions avec heure (dans l'ordre), puis celles « dans la journée »."""
    return (item.due_date, item.due_time is None, item.due_time or time(0), item.prospect_name)


def agenda(items: Iterable[AgendaItem], now: datetime, timezone: str) -> Agenda:
    today = now.astimezone(ZoneInfo(timezone)).date()
    tomorrow = today + timedelta(days=1)
    ordered = sorted(items, key=_order)
    return Agenda(
        [i for i in ordered if i.due_date < today],
        [i for i in ordered if i.due_date == today],
        [i for i in ordered if i.due_date == tomorrow],
    )
