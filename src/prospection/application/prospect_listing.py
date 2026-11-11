"""Liste des prospects et session d'appel (C57, C61, C109, C120, C127, C128)."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from itertools import groupby
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, Engine

from prospection.application.prospect_view import SCORE, Summary, all_domains, summarize
from prospection.domain.contact_label import MAILED, contact_label
from prospection.domain.prospect_source import ALL, Scope
from prospection.domain.text import without_controls
from prospection.storage import prospect_list as store
from prospection.storage.contact_marks import contact_marks
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
    scope: Scope = ALL  # celle appliquée : une campagne d'une autre origine est ignorée
    any_prospect: bool = False  # au moins un prospect, recherche et filtres mis à part
    groups: list[tuple[str, list[ProspectRow]]] = field(default_factory=list)  # par campagne
    contacted: dict[int, tuple[str, str]] = field(default_factory=dict)  # C184 : état, libellé
    contact_counts: dict[str, int] = field(default_factory=dict)  # « envoye », « non »


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


def _grouped(
    rows: list[ProspectRow], campaigns: list[tuple[int, str, int]]
) -> list[tuple[str, list[ProspectRow]]]:
    """Par campagne, la plus récente d'abord ; dans chaque campagne, le tri choisi (C133)."""
    other = (len(campaigns), "Autre campagne")
    rank = {c[0]: (i, c[1]) for i, c in enumerate(campaigns)}

    def key(row: ProspectRow) -> tuple[int, int]:
        return rank.get(row.campaign_id or 0, other)[0], row.campaign_id or 0

    ordered = sorted(rows, key=key)  # stable : le tri choisi est gardé dans chaque campagne
    return [
        (rank.get(cid or 0, other)[1], list(group))
        for cid, group in groupby(ordered, key=lambda r: r.campaign_id)
    ]


def _today(now: datetime | None, timezone: str) -> date:
    """Même date que la fiche : celle du fuseau du propriétaire (C57, seuils d'ancienneté)."""
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(timezone)).date()


def prospect_list(
    engine: Engine, status: str | None, query: str, sort: str, now: datetime | None = None,
    timezone: str = "Europe/Paris", scope: Scope = ALL, contact: str = "",
) -> ProspectList:  # fmt: skip
    """`scope` : une origine (Terrain à part, C127), éventuellement une campagne (C128) ;
    `contact` : « envoye » ou « non » (C184)."""
    query = clean_query(query)
    with engine.connect() as conn:
        campaigns = campaign_choices(conn, scope.source) if scope.source else []
        scope = _checked(scope, campaigns)
        rows, summaries = _listed(conn, status, query, sort, _today(now, timezone), scope)
        counts = store.status_counts(conn, query, scope)
        sources = store.source_counts(conn, query)
        any_prospect = bool(sources) or bool(store.source_counts(conn, ""))
        marks = contact_marks(conn, [r.id for r in rows])
    contacted = {
        pid: (kind, contact_label(kind, at, timezone)) for pid, (kind, at) in marks.items()
    }
    mailed = {pid for pid, (kind, _) in contacted.items() if kind in MAILED}
    contact_counts = {"envoye": len(mailed), "non": len(rows) - len(mailed)}
    rows = [r for r in rows if _shown(r.id in mailed, contact)]
    groups = _grouped(rows, campaigns)
    rows = [r for _, group in groups for r in group]
    return ProspectList(rows, counts, summaries, sources, campaigns, scope, any_prospect, groups,
                        contacted, contact_counts)  # fmt: skip


def _shown(mailed: bool, contact: str) -> bool:
    return contact not in ("envoye", "non") or mailed == (contact == "envoye")


def _checked(scope: Scope, campaigns: list[tuple[int, str, int]]) -> Scope:
    """Une campagne qui n'est pas de cet onglet (vieux lien) : toute la liste de l'onglet."""
    if scope.campaign_id is None or scope.campaign_id in {c[0] for c in campaigns}:
        return scope
    return Scope(scope.source)


def start_session(
    engine: Engine, status: str | None, query: str, sort: str, now: datetime,
    timezone: str = "Europe/Paris", scope: Scope = ALL, contact: str = "",
) -> int | None:  # fmt: skip
    """Fige la file affichée (même ordre que la liste) et renvoie le premier prospect à
    appeler (C109, C133)."""
    query = clean_query(query)
    with engine.begin() as conn:
        campaigns = campaign_choices(conn, scope.source) if scope.source else []
        scope = _checked(scope, campaigns)
        rows, _ = _listed(conn, status, query, sort, _today(now, timezone), scope)
        marks = contact_marks(conn, [r.id for r in rows]) if contact else {}
        mailed = {pid for pid, (kind, _) in marks.items() if kind in MAILED}
        rows = [r for r in rows if _shown(r.id in mailed, contact)]  # même liste qu'affichée
        queue = [r.id for _, group in _grouped(rows, campaigns) for r in group]
        store.start_session(conn, queue, now)
    return queue[0] if queue else None
