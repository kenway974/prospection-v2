"""Départements français (C13), depuis le fichier de données `data/departements.yaml`."""

from functools import cache
from importlib import resources

import yaml

from prospection.domain.campaign_request import DepartmentZone
from prospection.domain.trades import normalize


@cache
def load_departments() -> dict[str, str]:
    text = resources.files("prospection.data").joinpath("departements.yaml").read_text("utf-8")
    data = yaml.safe_load(text)
    return {str(code): str(name) for code, name in data.items()}


def find_department(text: str) -> DepartmentZone | None:
    """Par code (« 974 », « 2A ») ou par nom (« La Réunion »), accents et casse ignorés."""
    wanted = text.strip().upper()
    departments = load_departments()
    if wanted in departments:
        return DepartmentZone(wanted, departments[wanted])
    by_name = {normalize(name): code for code, name in departments.items()}
    code = by_name.get(normalize(text))
    return DepartmentZone(code, departments[code]) if code else None
