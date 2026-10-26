"""Rapprochement des prospects avec le registre (C44, C45)."""

from dataclasses import dataclass

from sqlalchemy import Connection, func, select, update

from prospection.domain.company import Company
from prospection.storage.company_codec import encode_company
from prospection.storage.schema_campaigns import prospects

SURE, TO_CONFIRM, NOT_FRENCH = "sûr", "à confirmer", "hors France"
TO_CONFIRM_FLAG = "Entreprise à confirmer"


@dataclass(frozen=True)
class Pending:
    id: int
    name: str
    address: str
    country: str


def pending_prospects(conn: Connection, limit: int) -> list[Pending]:
    """Prospects qualifiés pas encore rapprochés du registre, les plus anciens d'abord."""
    p = prospects.c
    rows = conn.execute(
        select(p.id, p.data_json).where(p.qualified.is_(True), p.registry_status.is_(None))
        .order_by(p.created_at, p.id).limit(limit)
    )  # fmt: skip
    return [
        Pending(r.id, str(r.data_json.get("name") or ""), str(r.data_json.get("address") or ""),
                str(r.data_json.get("country") or "FR"))
        for r in rows
    ]  # fmt: skip


def save_match(conn: Connection, prospect_id: int, company: Company | None, status: str) -> None:
    p = prospects.c
    values: dict[str, object] = {"registry_status": status}
    if company is not None:
        values["company_json"] = encode_company(company)
    if status == TO_CONFIRM:
        values["to_check"] = func.array_append(p.to_check, TO_CONFIRM_FLAG)
    conn.execute(update(prospects).where(p.id == prospect_id).values(**values))


def set_company(conn: Connection, campaign_id: int, place_id: str, company: Company) -> None:
    """Prospect venu du registre : l'entreprise est connue d'emblée."""
    p = prospects.c
    conn.execute(
        update(prospects).where(p.campaign_id == campaign_id, p.place_id == place_id)
        .values(company_json=encode_company(company), registry_status=SURE)
    )  # fmt: skip
