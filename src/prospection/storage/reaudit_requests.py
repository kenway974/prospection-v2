"""Nouveaux audits de site demandés depuis la fiche (C156)."""

from datetime import datetime

from sqlalchemy import Connection, select, update

from prospection.domain.place import Place
from prospection.domain.site_report import SiteReport
from prospection.storage.campaign_codec import decode_place
from prospection.storage.schema_campaigns import prospects
from prospection.storage.site_codec import decode_site, encode_site

_P = prospects.c


def request(conn: Connection, prospect_id: int, now: datetime) -> bool:
    done = conn.execute(
        update(prospects).where(_P.id == prospect_id).values(reaudit_requested_at=now)
    )
    return done.rowcount == 1


def requested(conn: Connection, prospect_id: int) -> bool:
    found = conn.execute(select(_P.reaudit_requested_at).where(_P.id == prospect_id)).scalar()
    return found is not None


def pending(
    conn: Connection, limit: int
) -> list[tuple[int, Place, tuple[str, ...], SiteReport | None]]:
    rows = conn.execute(
        select(_P.id, _P.data_json, _P.keywords, _P.site_json)
        .where(_P.reaudit_requested_at.is_not(None))
        .order_by(_P.reaudit_requested_at, _P.id).limit(limit)
    )  # fmt: skip
    return [
        (int(r.id), decode_place(r.data_json), tuple(r.keywords),
         decode_site(r.site_json) if r.site_json else None)
        for r in rows
    ]  # fmt: skip


def done(conn: Connection, prospect_id: int, report: SiteReport | None) -> None:
    """Demande traitée ; le nouveau rapport remplace l'ancien s'il y en a un."""
    values: dict[str, object] = {"reaudit_requested_at": None}
    if report is not None:
        values["site_json"] = encode_site(report)
    conn.execute(update(prospects).where(_P.id == prospect_id).values(**values))
