"""Entreprises à compléter (registre gratuit, puis registre national) (C149, C150)."""

from sqlalchemy import Connection, or_, select, update

from prospection.domain.company import Company
from prospection.storage.company_codec import decode_company, encode_company
from prospection.storage.registry_status import SURE
from prospection.storage.schema_campaigns import prospects


def pending_details(conn: Connection, with_rne: bool, limit: int) -> list[tuple[int, Company]]:
    """Prospects retenus dont l'entreprise sûre n'est pas encore complétée, les plus anciens
    d'abord ; `with_rne` : identifiants INPI saisis, le registre national compte aussi."""
    p = prospects.c
    missing = [p.company_json["detailed"].astext.is_distinct_from("true")]
    if with_rne:
        missing.append(p.company_json["rne_checked"].astext.is_distinct_from("true"))
    rows = conn.execute(
        select(p.id, p.company_json)
        .where(p.qualified.is_(True), p.registry_status == SURE, p.company_json.is_not(None),
               or_(*missing))
        .order_by(p.created_at, p.id).limit(limit)
    )  # fmt: skip
    return [(int(r.id), decode_company(r.company_json)) for r in rows]


def save_details(conn: Connection, prospect_id: int, company: Company) -> None:
    p = prospects.c
    conn.execute(
        update(prospects).where(p.id == prospect_id).values(company_json=encode_company(company))
    )
