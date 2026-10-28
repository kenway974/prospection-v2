"""Prospects trouvés par une campagne (C38, C42)."""

from datetime import datetime

from sqlalchemy import Connection, func, select, update
from sqlalchemy.dialects.postgresql import insert

from prospection.domain.call_status import TO_CALL
from prospection.domain.criteria import Verdict
from prospection.domain.place import Place
from prospection.domain.site_report import SiteReport
from prospection.storage.campaign_codec import encode_place
from prospection.storage.schema_campaigns import prospects
from prospection.storage.site_codec import encode_site


def insert_prospect(
    conn: Connection, campaign_id: int, place: Place, keyword: str, verdict: Verdict,
    now: datetime, site: SiteReport | None = None,
) -> bool:  # fmt: skip
    """Ajoute le prospect ; s'il existe déjà, ajoute seulement le mot-clé. Vrai si nouveau."""
    values = {
        "campaign_id": campaign_id, "place_id": place.place_id, "data_json": encode_place(place),
        "keywords": [keyword], "qualified": verdict.qualified, "reasons": list(verdict.reasons),
        "to_check": list(verdict.to_check), "status": TO_CALL if verdict.qualified else None,
        "created_at": now, "site_json": encode_site(site) if site else None,
    }  # fmt: skip
    statement = (
        insert(prospects)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_prospect_place")
        .returning(prospects.c.id)
    )
    if conn.execute(statement).first() is not None:
        return True
    p = prospects.c
    conn.execute(
        update(prospects)
        .where(p.campaign_id == campaign_id, p.place_id == place.place_id,
               ~p.keywords.contains([keyword]))
        .values(keywords=func.array_append(p.keywords, keyword))
    )  # fmt: skip
    return False


def exclusion_counts(conn: Connection, campaign_id: int) -> list[tuple[str, int]]:
    """Raisons d'exclusion (sans le détail entre parenthèses), les plus fréquentes d'abord."""
    p = prospects.c
    reason = func.split_part(func.unnest(p.reasons), " (", 1).label("reason")
    inner = select(reason).where(p.campaign_id == campaign_id).subquery()
    rows = conn.execute(
        select(inner.c.reason, func.count().label("n"))
        .group_by(inner.c.reason).order_by(func.count().desc(), inner.c.reason)
    )  # fmt: skip
    return [(r.reason, int(r.n)) for r in rows]


def known_places(conn: Connection, campaign_id: int, place_ids: list[str]) -> set[str]:
    """Établissements déjà enregistrés dans la campagne : leur site n'est pas relu (C38)."""
    p = prospects.c
    rows = conn.execute(
        select(p.place_id).where(p.campaign_id == campaign_id, p.place_id.in_(place_ids))
    )
    return {str(place_id) for (place_id,) in rows}


def new_qualified(conn: Connection, campaign_id: int) -> int:
    """Retenus jamais vus dans une campagne plus ancienne (C78)."""
    p, older = prospects.c, prospects.alias("older")
    seen = select(older.c.id).where(
        older.c.place_id == p.place_id, older.c.campaign_id < campaign_id
    )
    query = select(func.count()).where(
        p.campaign_id == campaign_id, p.qualified.is_(True), ~seen.exists()
    )
    return int(conn.execute(query).scalar_one())
