"""Rapprochement des prospects avec le registre (C44, C45)."""

from dataclasses import dataclass

from sqlalchemy import Connection, func, select, update

from prospection.domain.company import Company
from prospection.domain.company_card import NON_DIFFUSIBLE, NOT_FRENCH, SURE, TO_CONFIRM
from prospection.storage.company_codec import encode_company
from prospection.storage.schema_campaigns import prospects

__all__ = ["NON_DIFFUSIBLE", "NOT_FRENCH", "SURE", "TO_CONFIRM"]
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


def _company_values(company: Company | None, status: str) -> dict[str, object]:
    """Entreprise non diffusible (C93) : rien du registre n'est gardé, seulement ce statut."""
    if company is not None and not company.diffusible:
        return {"registry_status": NON_DIFFUSIBLE}
    if company is None:
        return {"registry_status": status}
    return {"registry_status": status, "company_json": encode_company(company)}


def save_match(conn: Connection, prospect_id: int, company: Company | None, status: str) -> None:
    p = prospects.c
    values = _company_values(company, status)
    if status == TO_CONFIRM:
        values["to_check"] = func.array_append(p.to_check, TO_CONFIRM_FLAG)
    conn.execute(update(prospects).where(p.id == prospect_id).values(**values))


def set_company(conn: Connection, campaign_id: int, place_id: str, company: Company) -> None:
    """Prospect venu du registre : l'entreprise est connue d'emblée."""
    p = prospects.c
    conn.execute(
        update(prospects).where(p.campaign_id == campaign_id, p.place_id == place_id)
        .values(**_company_values(company, SURE))
    )  # fmt: skip


def known_sirens(conn: Connection, campaign_id: int) -> set[str]:
    """Entreprises déjà enregistrées dans la campagne : jamais recherchées (ni payées) deux fois."""
    p = prospects.c
    rows = conn.execute(
        select(p.company_json["siren"].astext)
        .where(p.campaign_id == campaign_id, p.company_json.is_not(None))
    )  # fmt: skip
    return {str(siren) for (siren,) in rows if siren}
