"""Entreprise du registre : rapprochement sûr et présentation (C44, C45, C93)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib import resources

import yaml
from pydantic import BaseModel

from prospection.domain.place import Place
from prospection.domain.trades import normalize

_POSTAL = re.compile(r"\b(\d{5})\b")
_LEGAL_WORDS = {"sarl", "sas", "sasu", "eurl", "sa", "sci", "ei", "eirl", "snc", "selarl"}
NOT_PUBLISHED = "non publié"


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


@dataclass(frozen=True)
class Match:
    company: Company | None
    sure: bool


def postal_code(address: str) -> str | None:
    codes = _POSTAL.findall(address)
    return str(codes[-1]) if codes else None


def _words(name: str) -> frozenset[str]:
    return frozenset(w for w in normalize(name).split() if w not in _LEGAL_WORDS)


def same_name(a: str, b: str) -> bool:
    """Mêmes mots (hors forme juridique), ou l'un contient tous les mots de l'autre (2 au moins)."""
    small, big = sorted((_words(a), _words(b)), key=len)
    return bool(small) and (small == big or (len(small) >= 2 and small <= big))


def match_company(name: str, postal: str | None, candidates: Sequence[Company]) -> Match:
    """Sûr seulement si un seul candidat a le même nom et le même code postal (C45)."""
    sure = [
        c for c in candidates
        if postal and c.postal_code == postal
        and any(same_name(name, n) for n in (c.name, *c.other_names))
    ]  # fmt: skip
    return Match(sure[0], True) if len(sure) == 1 else Match(None, False)


def match_place(company: Company, places: Sequence[Place]) -> Place | None:
    """La fiche Google de l'entreprise, seulement si une seule a le même nom et code postal."""
    names = (company.name, *company.other_names)
    sure = [
        p for p in places
        if company.postal_code and postal_code(p.address) == company.postal_code
        and any(same_name(p.name, n) for n in names)
    ]  # fmt: skip
    return sure[0] if len(sure) == 1 else None


class _Labels(BaseModel):
    formes: dict[str, str]
    effectifs: dict[str, str]


@cache
def _labels() -> _Labels:
    text = resources.files("prospection.data").joinpath("registre.yaml").read_text("utf-8")
    return _Labels.model_validate(yaml.safe_load(text))


def _euros(value: int | None) -> str:
    return NOT_PUBLISHED if value is None else f"{value:,}".replace(",", " ") + " €"


def describe(company: Company) -> list[tuple[str, str]]:
    """Lignes « L'entreprise » ; jamais rien d'inventé, « non publié » quand l'info manque."""
    if not company.diffusible:
        return [("Registre", "Données non diffusées à la demande de l'entreprise.")]
    labels, s = _labels(), company.siren
    form = company.legal_form
    lines = [
        ("SIREN", f"{s[:3]} {s[3:6]} {s[6:]}"),
        ("Création", company.created.strftime("%d/%m/%Y") if company.created else NOT_PUBLISHED),
        ("Forme", labels.formes.get(form, f"autre forme (code {form})") if form else NOT_PUBLISHED),
        ("Activité", company.naf or NOT_PUBLISHED),
        ("Effectif", labels.effectifs.get(company.workforce or "", NOT_PUBLISHED)),
        ("Dirigeants", ", ".join(company.leaders) or NOT_PUBLISHED),
    ]  # fmt: skip
    if company.finances:
        year, revenue, result = company.finances
        return [*lines, (f"Chiffre d'affaires {year}", _euros(revenue)),
                (f"Résultat {year}", _euros(result))]  # fmt: skip
    return [*lines, ("Chiffre d'affaires", NOT_PUBLISHED)]
