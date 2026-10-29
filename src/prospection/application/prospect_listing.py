"""Liste des prospects et session d'appel (C57, C61, C109, C120, C127, C128)."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, Engine

from prospection.application.prospect_view import SCORE, Summary, all_domains, summarize
from prospection.domain.prospect_source import ALL, Scope
from prospection.domain.text import without_controls
from prospection.storage import prospect_list as store
from prospection.storage.mail_domains import mail_servers
from prospection.storage.prospect_list import ProspectRow
from prospection.storage.prospect_scope import campaign_choices


@dataclass(frozen=True)
class ProspectList:
    rows: list[ProspectRow]
    counts: dict[str, int]
    summaries: dict[int, Summary] = field(default_factory=dict)
    sources: dict[str, int] = field(default_factory=dict)  # par origine (à appeler, Terrain)
    campaigns: list[tuple[int, str, int]] = field(default_factory=list)  # de cette origine


def clean_query(query: str) -> str:
    return without_controls(query)[:100]


def _listed(
    conn: Connection, status: str | None, query: str, sort: str, today: date, scope: Scope
) -> tuple[list[ProspectRow], dict[int, Summary]]:
    """Lignes et résumés, chaque score calculé une seule fois ; tri « score » ici (C57)."""
    rows = store.prospect_rows(conn, status, query, "trouves" if sort == SCORE else sort, scope)
    servers = mail_servers(conn, all_domains(rows))
    summaries = {r.id: summarize(r, today, servers) for r in rows}
    if sort == SCORE:  # meilleures d'abord ; à score égal, l'ordre de la recherche
        rows = sorted(rows, key=lambda r: -summaries[r.id].score)
    return rows, summaries


def _today(now: datetime | None, timezone: str) -> date:
    """Même date que la fiche : celle du fuseau du propriétaire (C57, seuils d'ancienneté)."""
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(timezone)).date()


def prospect_list(
    engine: Engine, status: str | None, query: str, sort: str, now: datetime | None = None,
    timezone: str = "Europe/Paris", scope: Scope = ALL,
) -> ProspectList:  # fmt: skip
    """`scope` : une origine (Terrain à part, C127), éventuellement une campagne (C128)."""
    query = clean_query(query)
    with engine.connect() as conn:
        rows, summaries = _listed(conn, status, query, sort, _today(now, timezone), scope)
        counts = store.status_counts(conn, query, scope)
        sources = store.source_counts(conn, query)
        campaigns = campaign_choices(conn, scope.source) if scope.source else []
    return ProspectList(rows, counts, summaries, sources, campaigns)


def start_session(
    engine: Engine, status: str | None, query: str, sort: str, now: datetime,
    timezone: str = "Europe/Paris", scope: Scope = ALL,
) -> int | None:  # fmt: skip
    """Fige la file affichée et renvoie le premier prospect à appeler (C109)."""
    query = clean_query(query)
    with engine.begin() as conn:
        if sort == SCORE:
            rows, _ = _listed(conn, status, query, sort, _today(now, timezone), scope)
            queue = [r.id for r in rows]
        else:
            queue = store.prospect_ids(conn, status, query, sort, scope)
        store.start_session(conn, queue, now)
    return queue[0] if queue else None
