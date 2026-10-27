"""Entreprises récemment créées : API Sirene 3.11 de l'INSEE (clé du propriétaire).

Syntaxe `q` vérifiée sur le client officiel de l'INSEE (pynsee) : intervalle de dates
`[A TO B]`, variables historisées dans `periode(...)`, joker `*`. Les établissements non
diffusibles (opposition) ne sont jamais proposés (C93).
"""

from dataclasses import dataclass
from datetime import date

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.company import Company
from prospection.domain.key_check import KeyCheck
from prospection.domain.place import clip
from prospection.http_client import json_object, send
from prospection.sources.company_registry import RegistryUnavailable
from prospection.sources.insee import BASE_URL, LABEL

PAGE_SIZE = 20
KEY_REFUSED = (
    "Clé Sirène refusée : vérifiez-la dans Réglages → Clés API (abonnement à l'API Sirene)."
)


class SireneRefused(Exception):
    """La clé est refusée ; le message dit quoi faire."""


@dataclass(frozen=True)
class RecentQuery:
    since: date
    until: date
    area: str  # « commune » (code INSEE) ou « departement »
    code: str
    naf_prefixes: tuple[str, ...]


@dataclass(frozen=True)
class SirenePage:
    companies: list[Company]
    next_cursor: str | None


def sirene_q(query: RecentQuery) -> str:
    parts = [f"dateCreationEtablissement:[{query.since.isoformat()} TO {query.until.isoformat()}]"]
    if query.area == "commune":
        parts.append(f"codeCommuneEtablissement:{query.code}")
    else:
        prefix = "20" if query.code in ("2A", "2B") else query.code
        parts.append(f"codePostalEtablissement:{prefix}*")
    parts += ["statutDiffusionEtablissement:O", "periode(etatAdministratifEtablissement:A)"]
    if query.naf_prefixes:
        nafs = " OR ".join(
            f"periode(activitePrincipaleEtablissement:{p}*)" for p in query.naf_prefixes
        )
        parts.append(f"({nafs})")
    return " AND ".join(parts)


class _Legal(BaseModel):
    denominationUniteLegale: str | None = None
    nomUniteLegale: str | None = None
    prenom1UniteLegale: str | None = None
    categorieJuridiqueUniteLegale: str | None = None
    dateCreationUniteLegale: date | None = None


class _Address(BaseModel):
    codePostalEtablissement: str | None = None
    libelleCommuneEtablissement: str | None = None


class _Period(BaseModel):
    dateFin: date | None = None
    etatAdministratifEtablissement: str | None = None
    activitePrincipaleEtablissement: str | None = None
    enseigne1Etablissement: str | None = None
    denominationUsuelleEtablissement: str | None = None


class _Etab(BaseModel):
    siren: str
    statutDiffusionEtablissement: str | None = None
    dateCreationEtablissement: date | None = None
    trancheEffectifsEtablissement: str | None = None
    uniteLegale: _Legal = _Legal()
    adresseEtablissement: _Address = _Address()
    periodesEtablissement: list[_Period] = []


def _company(e: _Etab) -> Company:
    legal, address = e.uniteLegale, e.adresseEtablissement
    current = next((p for p in e.periodesEtablissement if p.dateFin is None), _Period())
    person = " ".join(n for n in (legal.prenom1UniteLegale, legal.nomUniteLegale) if n)
    signs = [
        s for s in (current.enseigne1Etablissement, current.denominationUsuelleEtablissement) if s
    ]
    return Company(
        siren=e.siren[:9], name=clip(legal.denominationUniteLegale or person, 200) or "",
        other_names=tuple(clip(s, 200) or "" for s in signs),
        postal_code=address.codePostalEtablissement,
        city=clip(address.libelleCommuneEtablissement, 100),
        created=legal.dateCreationUniteLegale or e.dateCreationEtablissement,
        active=current.etatAdministratifEtablissement != "F",
        legal_form=legal.categorieJuridiqueUniteLegale,
        naf=current.activitePrincipaleEtablissement, workforce=e.trancheEffectifsEtablissement,
        leaders=(), finances=None, diffusible=True,
    )  # fmt: skip


def recent_companies(client: httpx.Client, key: str, query: RecentQuery, cursor: str) -> SirenePage:
    headers = {"X-INSEE-Api-Key-Integration": key, "Accept": "application/json"}
    params = {"q": sirene_q(query), "nombre": str(PAGE_SIZE), "curseur": cursor}
    response = send(client, "GET", f"{BASE_URL}/siret", LABEL, headers=headers, params=params)
    if (
        isinstance(response, KeyCheck)
        or response.status_code in (429,)
        or response.status_code >= 500
    ):
        raise RegistryUnavailable
    if response.status_code in (401, 403):
        raise SireneRefused(KEY_REFUSED)
    if response.status_code == 404:  # Sirene répond 404 quand rien ne correspond
        return SirenePage([], None)
    body = json_object(response)
    if response.status_code != 200 or body is None:
        raise RegistryUnavailable
    companies = []
    raw = body.get("etablissements")
    for item in raw if isinstance(raw, list) else []:
        try:
            etab = _Etab.model_validate(item)
        except ValidationError:
            continue
        if etab.statutDiffusionEtablissement == "O":
            companies.append(_company(etab))
    header = body.get("header")
    following = header.get("curseurSuivant") if isinstance(header, dict) else None
    if not isinstance(following, str) or following == cursor or not companies:
        return SirenePage(companies, None)
    return SirenePage(companies, following[:500])
