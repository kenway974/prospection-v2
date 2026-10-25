"""Départements français (C13), depuis le fichier de données `data/departements.yaml`."""

from functools import cache
from importlib import resources
from typing import Annotated

import yaml
from pydantic import RootModel, StringConstraints, ValidationError

from prospection.domain.campaign_request import DepartmentZone
from prospection.domain.trades import normalize

Code = Annotated[str, StringConstraints(pattern=r"^(\d{2}|2[AB]|97\d)$")]
Name = Annotated[str, StringConstraints(min_length=1, max_length=60)]


class InvalidDepartmentFile(ValueError):
    pass


def parse_departments(text: str) -> dict[str, str]:
    try:
        raw = yaml.safe_load(text)
        if isinstance(raw, dict):
            raw = {str(code): name for code, name in raw.items()}
        return RootModel[dict[Code, Name]].model_validate(raw).root
    except (yaml.YAMLError, ValidationError) as error:
        raise InvalidDepartmentFile(f"Fichier des départements invalide : {error}") from None


@cache
def load_departments() -> dict[str, str]:
    text = resources.files("prospection.data").joinpath("departements.yaml").read_text("utf-8")
    return parse_departments(text)


def find_department(text: str) -> DepartmentZone | None:
    """Par code (« 974 », « 2A ») ou par nom (« La Réunion »), accents et casse ignorés."""
    wanted = text.strip().upper()
    departments = load_departments()
    if wanted in departments:
        return DepartmentZone(wanted, departments[wanted])
    by_name = {normalize(name): code for code, name in departments.items()}
    code = by_name.get(normalize(text))
    return DepartmentZone(code, departments[code]) if code else None
