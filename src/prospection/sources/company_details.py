"""Compléments d'une entreprise connue par son SIREN, dans l'API Recherche d'entreprises
(gratuite, sans clé) : labels, établissements ouverts, activité du siège (C149).

Utile surtout pour les entreprises venues de Sirène, qui n'ont ni dirigeants ni chiffres.
Une entreprise non diffusible ne garde rien de plus (C93).
"""

import dataclasses
from typing import Any

import httpx
from pydantic import ValidationError

from prospection.domain.company import Company
from prospection.domain.key_check import KeyCheck
from prospection.http_client import json_object, send
from prospection.sources.company_registry import (
    SEARCH_URL,
    RegistryRejected,
    RegistryResult,
    RegistryUnavailable,
    to_company,
)

LABELS = ("est_rge", "est_qualiopi", "est_bio", "est_ess", "est_patrimoine_vivant",
          "est_societe_mission", "est_organisme_formation", "est_entrepreneur_spectacle",
          "est_finess", "est_siae", "est_alim_confiance", "est_achats_responsables")  # fmt: skip


def _labels(complements: dict[str, Any] | None) -> tuple[str, ...]:
    found = complements or {}
    return tuple(name for name in LABELS if found.get(name) is True)


def with_details(r: RegistryResult) -> Company:
    company = to_company(r)
    if not company.diffusible:
        return company
    sites, siege = r.nombre_etablissements_ouverts, r.siege
    return dataclasses.replace(
        company, labels=_labels(r.complements),
        site_naf=siege.activite_principale if siege else None,
        open_sites=sites if sites is not None and 0 <= sites < 1_000_000 else None,
    )  # fmt: skip


def company_by_siren(client: httpx.Client, siren: str) -> Company | None:
    """L'entreprise de ce SIREN, ou None si le registre ne la connaît pas."""
    response = send(client, "GET", SEARCH_URL, "Registre des entreprises",
                    params={"q": siren, "per_page": 5})  # fmt: skip
    if isinstance(response, KeyCheck) or response.status_code == 429:
        raise RegistryUnavailable
    if 400 <= response.status_code < 500:
        raise RegistryRejected
    body = json_object(response) if response.status_code == 200 else None
    if body is None:
        raise RegistryUnavailable
    results = body.get("results")
    for raw in results if isinstance(results, list) else []:
        try:
            found = RegistryResult.model_validate(raw)
        except ValidationError:
            continue
        if found.siren == siren:
            return with_details(found)
    return None
