"""Prospects trouvés par une campagne (C38, C42)."""

from datetime import datetime

from sqlalchemy import Connection, func, select, update
from sqlalchemy.dialects.postgresql import insert

from prospection.domain.criteria import Verdict
from prospection.domain.place import Place
from prospection.storage.campaign_codec import encode_place
from prospection.storage.schema_campaigns import prospects

TO_CALL = "à appeler"


def insert_prospect(
    conn: Connection, campaign_id: int, place: Place, keyword: str, verdict: Verdict,
    now: datetime,
) -> bool:  # fmt: skip
    """Ajoute le prospect ; s'il existe déjà, ajoute seulement le mot-clé. Vrai si nouveau."""
    values = {
        "campaign_id": campaign_id, "place_id": place.place_id, "data_json": encode_place(place),
        "keywords": [keyword], "qualified": verdict.qualified, "reasons": list(verdict.reasons),
        "to_check": list(verdict.to_check), "status": TO_CALL if verdict.qualified else None,
        "created_at": now,
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
