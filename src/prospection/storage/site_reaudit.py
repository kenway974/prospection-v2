"""Sites à réauditer : audits faits avant la nouvelle détection (sans emplacement du
formulaire) (C152)."""

from sqlalchemy import Connection, select, update

from prospection.domain.place import Place
from prospection.domain.site_report import SiteReport
from prospection.storage.campaign_codec import decode_place
from prospection.storage.schema_campaigns import prospects
from prospection.storage.site_codec import decode_site, encode_site

_P = prospects.c


def pending_reaudits(
    conn: Connection, limit: int
) -> list[tuple[int, Place, tuple[str, ...], SiteReport]]:
    """Prospects retenus dont l'audit n'a pas d'emplacement du formulaire, plus anciens d'abord."""
    audit = _P.site_json["audit"]
    rows = conn.execute(
        select(_P.id, _P.data_json, _P.keywords, _P.site_json)
        .where(_P.qualified.is_(True), audit.astext.is_not(None),
               audit["form_place"].astext.is_(None))
        .order_by(_P.created_at, _P.id).limit(limit)
    )  # fmt: skip
    found = []
    for r in rows:
        old = decode_site(r.site_json)
        if old is not None:
            found.append((int(r.id), decode_place(r.data_json), tuple(r.keywords), old))
    return found


def save_reaudit(conn: Connection, prospect_id: int, report: SiteReport) -> None:
    conn.execute(
        update(prospects).where(_P.id == prospect_id).values(site_json=encode_site(report))
    )
