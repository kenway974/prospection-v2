"""Entreprise du registre : rapprochement sûr et présentation (C44, C45, C93)."""

import dataclasses
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from prospection.domain.place import Place
from prospection.domain.trades import normalize

_POSTAL = re.compile(r"\b(\d{5})\b")
# Mots d'un nom qui ne le distinguent pas (forme juridique, mots de liaison) : une seule liste
LEGAL_WORDS = frozenset({
    "sarl", "sas", "sasu", "eurl", "sa", "sci", "ei", "eirl", "snc", "selarl", "ets",
    "etablissements", "entreprise", "ste", "societe",
})  # fmt: skip
LINK_WORDS = frozenset({"de", "du", "des", "la", "le", "les", "l", "d", "et", "a", "au", "aux",
                        "en", "chez"})  # fmt: skip


@dataclass(frozen=True)
class Company:
    siren: str
    name: str
    other_names: tuple[str, ...]  # enseignes, nom commercial
    postal_code: str | None
    city: str | None
    created: date | None
    active: bool
    legal_form: str | None  # code INSEE
    naf: str | None
    workforce: str | None  # tranche d'effectif INSEE
    leaders: tuple[str, ...]
    finances: tuple[int, int | None, int | None] | None  # année, CA, résultat
    diffusible: bool
    siret: str | None = None
    branches: tuple[tuple[str, str], ...] = ()  # (SIRET, code postal) des établissements trouvés
    labels: tuple[str, ...] = ()  # compléments du registre vrais (est_rge…) (C149)
    open_sites: int | None = None  # établissements ouverts
    site_naf: str | None = None  # activité de l'établissement (siège), si connue
    purpose: str | None = None  # objet social déclaré au RNE (C150)
    activities: tuple[str, ...] = ()  # activités déclarées au RNE, avec leur forme d'exercice
    domains: tuple[str, ...] = ()  # noms de domaine déclarés au RNE
    detailed: bool = False  # compléments du registre gratuit déjà cherchés (C149)
    rne_checked: bool = False  # registre national (INPI) déjà consulté (C150)


@dataclass(frozen=True)
class Match:
    company: Company | None
    sure: bool


def postal_code(address: str) -> str | None:
    codes = _POSTAL.findall(address)
    return str(codes[-1]) if codes else None


def _words(name: str) -> frozenset[str]:
    return frozenset(w for w in normalize(name).split() if w not in LEGAL_WORDS)


def same_name(a: str, b: str, city: str | None = None) -> bool:
    """Mêmes mots (hors forme juridique) ; l'un peut en avoir en plus (2 mots communs au
    moins) seulement si ce sont le nom de la ville ou des mots de liaison (C45)."""
    small, big = sorted((_words(a), _words(b)), key=len)
    allowed = LINK_WORDS | _words(city or "")
    return bool(small) and (small == big or (len(small) >= 2 and small <= big
                                             and big - small <= allowed))  # fmt: skip


def _site_here(company: Company, postal: str) -> tuple[bool, str | None]:
    """L'entreprise a-t-elle un établissement à ce code postal (siège ou autre), et son SIRET."""
    if company.postal_code == postal:
        return True, company.siret
    return next(
        ((True, siret) for siret, code in company.branches if code == postal), (False, None)
    )


def match_company(name: str, postal: str | None, candidates: Sequence[Company]) -> Match:
    """Sûr seulement si une seule entreprise active a le même nom et un établissement à ce
    code postal (C45). Le SIRET retenu est celui de cet établissement."""
    sure = [
        (c, site) for c in candidates
        if postal and c.active and (site := _site_here(c, postal))[0]
        and any(same_name(name, n, c.city) for n in (c.name, *c.other_names))
    ]  # fmt: skip
    if len(sure) != 1:
        return Match(None, False)
    company, (_, siret) = sure[0]
    return Match(dataclasses.replace(company, siret=siret, branches=()), True)


def match_place(company: Company, places: Sequence[Place]) -> Place | None:
    """La fiche Google de l'entreprise, seulement si une seule a le même nom et code postal."""
    names = (company.name, *company.other_names)
    sure = [
        p for p in places
        if company.postal_code and postal_code(p.address) == company.postal_code
        and any(same_name(p.name, n, company.city) for n in names)
    ]  # fmt: skip
    return sure[0] if len(sure) == 1 else None


def with_registry(base: Company, found: Company | None) -> Company:
    """Compléments du registre gratuit (C149) : dirigeants et chiffres s'ils manquaient,
    labels, établissements. Rien de plus pour une entreprise non diffusible (C93)."""
    if found is None or not found.diffusible:
        return dataclasses.replace(base, detailed=True)
    return dataclasses.replace(
        base, leaders=base.leaders or found.leaders, finances=base.finances or found.finances,
        labels=found.labels, open_sites=found.open_sites, site_naf=found.site_naf, detailed=True,
    )  # fmt: skip


def with_rne(
    base: Company, purpose: str | None, activities: tuple[str, ...], domains: tuple[str, ...]
) -> Company:
    """Ce que l'entreprise a déclaré au registre national (C150)."""
    return dataclasses.replace(base, purpose=purpose, activities=activities, domains=domains,
                               rne_checked=True)  # fmt: skip
