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
    labels: dict[str, str]


def _read(name: str) -> object:
    return yaml.safe_load(resources.files("prospection.data").joinpath(name).read_text("utf-8"))


@cache
def labels() -> _Labels:
    return _Labels.model_validate(_read("registre.yaml"))


@cache
def _activities() -> dict[str, str]:
    raw = _read("naf.yaml")
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def euros(value: int | None) -> str:
    return NOT_PUBLISHED if value is None else f"{value:,}".replace(",", " ") + " €"


def _activity(naf: str | None) -> str:
    if not naf:
        return NOT_PUBLISHED
    label = _activities().get(naf)
    return f"{label} ({naf})" if label else naf


def describe(company: Company) -> list[tuple[str, str]]:
    """Identité de l'entreprise ; jamais rien d'inventé, « non publié » quand l'info manque."""
    if not company.diffusible:
        return [("Registre", MESSAGES[NON_DIFFUSIBLE])]
    names, s, siret = labels(), company.siren, company.siret
    form = company.legal_form
    lines = [
        ("SIREN", f"{s[:3]} {s[3:6]} {s[6:]}"),
        *([("SIRET", f"{siret[:3]} {siret[3:6]} {siret[6:9]} {siret[9:]}")] if siret else []),
        ("Création", company.created.strftime("%d/%m/%Y") if company.created else NOT_PUBLISHED),
        ("Forme", names.formes.get(form, f"autre forme (code {form})") if form else NOT_PUBLISHED),
        ("Activité", _activity(company.naf)),
        ("Dirigeants", ", ".join(company.leaders) or NOT_PUBLISHED),
    ]  # fmt: skip
    return lines + _details(company)  # chiffres et effectif : bloc « Santé » (C112)


def _details(company: Company) -> list[tuple[str, str]]:
    """Compléments (C149, C150) : seulement ce qui est connu, rien d'inventé."""
    names, c = labels().labels, company
    found = [
        (c.site_naf and c.site_naf != c.naf, "Activité de l'établissement", _activity(c.site_naf)),
        (c.open_sites, "Établissements ouverts", str(c.open_sites)),
        (c.labels, "Labels", ", ".join(names.get(x, x) for x in c.labels)),
        (c.purpose, "Objet social", c.purpose or ""),
        (c.activities, "Activités déclarées", " ; ".join(c.activities)),
        (c.domains, "Sites déclarés", ", ".join(c.domains)),
    ]  # fmt: skip
    return [(label, value) for shown, label, value in found if shown]


def registry_lines(company: Company | None, status: str | None) -> list[tuple[str, str]]:
    """Ce que la fiche montre : l'entreprise si elle est connue, sinon où en est la recherche."""
    if company is not None:
        return describe(company)
    return [("Registre", MESSAGES.get(status, MESSAGES[None]))]
