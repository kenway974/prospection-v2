"""API Recherche d'entreprises (recherche-entreprises.api.gouv.fr) : gratuite, sans clé.

Format vérifié sur la spécification OpenAPI du dépôt officiel
annuaire-entreprises-data-gouv-fr/search-api. Chaque résultat est validé ; un résultat
invalide est ignoré, un champ absent reste inconnu (jamais inventé).
"""

from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.company import Company
from prospection.domain.key_check import KeyCheck
from prospection.domain.place import clip
from prospection.http_client import json_object, send

SEARCH_URL = "https://recherche-entreprises.api.gouv.fr/search"


class RegistryUnavailable(Exception):
    """Le registre ne répond pas ou demande de ralentir : réessayer plus tard."""


class RegistryRejected(Exception):
    """Le registre refuse cette recherche-là (4xx) : inutile de la refaire."""


class _Site(BaseModel):
    siret: str
    code_postal: str


class _Siege(BaseModel):
    siret: str | None = None
    code_postal: str | None = None
    libelle_commune: str | None = None
    liste_enseignes: list[str] | None = None
    nom_commercial: str | None = None
    statut_diffusion_etablissement: str | None = None
    activite_principale: str | None = None


class _Leader(BaseModel):
    nom: str | None = None
    prenoms: str | None = None
    denomination: str | None = None
    qualite: str | None = None


class _Bilan(BaseModel):
    ca: int | None = None
    resultat_net: int | None = None


class RegistryResult(BaseModel):
    siren: str
    nom_complet: str | None = None
    nom_raison_sociale: str | None = None
    date_creation: date | None = None
    etat_administratif: str | None = None
    nature_juridique: str | None = None
    activite_principale: str | None = None
    tranche_effectif_salarie: str | None = None
    statut_diffusion: str | None = None
    siege: _Siege | None = None
    dirigeants: list[_Leader] | None = None
    finances: dict[str, _Bilan] | None = None
    matching_etablissements: list[Any] | None = None
    complements: dict[str, Any] | None = None
    nombre_etablissements_ouverts: int | None = None


def _sites(raw: list[Any] | None) -> tuple[tuple[str, str], ...]:
    """Établissements correspondant à la recherche ; un établissement illisible est ignoré."""
    sites = []
    for item in (raw or [])[:10]:
        try:
            site = _Site.model_validate(item)
        except ValidationError:
            continue
        sites.append((site.siret[:14], site.code_postal[:5]))
    return tuple(sites)


def _leader(leader: _Leader) -> str:
    who = leader.denomination or " ".join(p for p in (leader.prenoms, leader.nom) if p)
    return clip(f"{who} ({leader.qualite})" if leader.qualite else who, 120) or ""


def _finances(raw: dict[str, _Bilan] | None) -> tuple[int, int | None, int | None] | None:
    years = sorted(int(y) for y in (raw or {}) if y.isdigit())
    if not years or raw is None:
        return None
    latest = raw[str(years[-1])]
    return years[-1], latest.ca, latest.resultat_net


def to_company(r: RegistryResult) -> Company:
    siege = r.siege or _Siege()
    diffusible = r.statut_diffusion != "P" and siege.statut_diffusion_etablissement != "P"
    others = [
        *(siege.liste_enseignes or []),
        *([siege.nom_commercial] if siege.nom_commercial else []),
    ]
    return Company(
        siren=r.siren[:9], name=clip(r.nom_raison_sociale or r.nom_complet, 200) or "",
        other_names=tuple(clip(n, 200) or "" for n in others[:5]),
        postal_code=siege.code_postal, city=clip(siege.libelle_commune, 100),
        created=r.date_creation,
        active=r.etat_administratif != "C", legal_form=r.nature_juridique,
        naf=r.activite_principale, workforce=r.tranche_effectif_salarie,
        leaders=tuple(_leader(d) for d in (r.dirigeants or [])[:5]) if diffusible else (),
        finances=_finances(r.finances) if diffusible else None, diffusible=diffusible,
        siret=siege.siret[:14] if siege.siret else None, branches=_sites(r.matching_etablissements),
    )  # fmt: skip


def search_companies(client: httpx.Client, name: str, postal: str | None) -> list[Company]:
    """Entreprises actives portant ce nom (et ce code postal s'il est connu), 5 au plus."""
    if not name.strip():
        return []
    params: dict[str, Any] = {"q": name.strip()[:100], "per_page": 5, "etat_administratif": "A"}
    if postal:
        params["code_postal"] = postal
    response = send(client, "GET", SEARCH_URL, "Registre des entreprises", params=params)
    if isinstance(response, KeyCheck) or response.status_code == 429:
        raise RegistryUnavailable
    if 400 <= response.status_code < 500:
        raise RegistryRejected
    if response.status_code != 200:
        raise RegistryUnavailable
    body = json_object(response)
    if body is None:
        raise RegistryUnavailable
    companies = []
    raw_results = body.get("results")
    for raw in raw_results if isinstance(raw_results, list) else []:
        try:
            companies.append(to_company(RegistryResult.model_validate(raw)))
        except ValidationError:
            continue
    return companies
