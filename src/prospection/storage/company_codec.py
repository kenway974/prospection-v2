"""Entreprise du registre <-> JSON (stockage)."""

from dataclasses import asdict
from datetime import date
from typing import Any

from prospection.domain.company import Company


def encode_company(company: Company) -> dict[str, Any]:
    data = asdict(company)
    data["created"] = company.created.isoformat() if company.created else None
    return data


def decode_company(data: dict[str, Any]) -> Company:
    values = dict(data)
    values["created"] = date.fromisoformat(values["created"]) if values["created"] else None
    values["other_names"] = tuple(values["other_names"])
    values["leaders"] = tuple(values["leaders"])
    values["finances"] = tuple(values["finances"]) if values["finances"] else None
    values["branches"] = tuple(tuple(b) for b in values.get("branches", ()))
    for name in ("labels", "activities", "domains"):  # absents des anciennes fiches
        values[name] = tuple(values.get(name, ()))
    return Company(**values)
