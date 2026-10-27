"""Bloc « L'entreprise » de la fiche : ce que dit le registre, en clair (C44, C93)."""

from functools import cache
from importlib import resources

import yaml
from pydantic import BaseModel

from prospection.domain.company import Company

SURE, TO_CONFIRM, NOT_FRENCH, NON_DIFFUSIBLE = "sûr", "à confirmer", "hors France", "non diffusible"
NOT_PUBLISHED = "non publié"
MESSAGES = {
    None: "Pas encore rapprochée du registre des entreprises.",
    TO_CONFIRM: "Entreprise pas trouvée avec certitude dans le registre : à confirmer.",
    NOT_FRENCH: "Établissement hors de France : registre français non consulté.",
    NON_DIFFUSIBLE: "Données non diffusées à la demande de l'entreprise.",
}


class _Labels(BaseModel):
    formes: dict[str, str]
    effectifs: dict[str, str]


def _read(name: str) -> object:
    return yaml.safe_load(resources.files("prospection.data").joinpath(name).read_text("utf-8"))


@cache
def _labels() -> _Labels:
    return _Labels.model_validate(_read("registre.yaml"))


@cache
def _activities() -> dict[str, str]:
    raw = _read("naf.yaml")
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def _euros(value: int | None) -> str:
    return NOT_PUBLISHED if value is None else f"{value:,}".replace(",", " ") + " €"


def _activity(naf: str | None) -> str:
    if not naf:
        return NOT_PUBLISHED
    label = _activities().get(naf)
    return f"{label} ({naf})" if label else naf


def describe(company: Company) -> list[tuple[str, str]]:
    """Lignes « L'entreprise » ; jamais rien d'inventé, « non publié » quand l'info manque."""
    if not company.diffusible:
        return [("Registre", MESSAGES[NON_DIFFUSIBLE])]
    labels, s, siret = _labels(), company.siren, company.siret
    form = company.legal_form
    lines = [
        ("SIREN", f"{s[:3]} {s[3:6]} {s[6:]}"),
        *([("SIRET", f"{siret[:3]} {siret[3:6]} {siret[6:9]} {siret[9:]}")] if siret else []),
        ("Création", company.created.strftime("%d/%m/%Y") if company.created else NOT_PUBLISHED),
        ("Forme", labels.formes.get(form, f"autre forme (code {form})") if form else NOT_PUBLISHED),
        ("Activité", _activity(company.naf)),
        ("Effectif", labels.effectifs.get(company.workforce or "", NOT_PUBLISHED)),
        ("Dirigeants", ", ".join(company.leaders) or NOT_PUBLISHED),
    ]  # fmt: skip
    if company.finances:
        year, revenue, result = company.finances
        return [*lines, (f"Chiffre d'affaires {year}", _euros(revenue)),
                (f"Résultat {year}", _euros(result))]  # fmt: skip
    return [*lines, ("Chiffre d'affaires", NOT_PUBLISHED)]


def registry_lines(company: Company | None, status: str | None) -> list[tuple[str, str]]:
    """Ce que la fiche montre : l'entreprise si elle est connue, sinon où en est la recherche."""
    if company is not None:
        return describe(company)
    return [("Registre", MESSAGES.get(status, MESSAGES[None]))]
