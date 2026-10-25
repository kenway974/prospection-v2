"""Demande de campagne et sa validation (C10 à C14, C17)."""

from dataclasses import dataclass

from prospection.domain.criteria import Criteria

MAX_TARGET = 200
MAX_RADIUS_KM = 50


def _department(insee_code: str) -> str:
    return insee_code[:3] if insee_code.startswith("97") else insee_code[:2]


@dataclass(frozen=True)
class CityZone:
    name: str
    insee_code: str
    lat: float
    lon: float

    @property
    def label(self) -> str:
        return f"{self.name} ({_department(self.insee_code)})"


@dataclass(frozen=True)
class RadiusZone:
    city: CityZone
    radius_km: int

    @property
    def label(self) -> str:
        return f"{self.radius_km} km autour de {self.city.label}"


@dataclass(frozen=True)
class DepartmentZone:
    code: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"


Zone = CityZone | RadiusZone | DepartmentZone


@dataclass(frozen=True)
class RawRequest:
    name: str
    trades: list[str]
    zones: list[Zone]
    target: int
    criteria: Criteria
    synonyms_on: bool


@dataclass(frozen=True)
class CampaignRequest:
    name: str
    trades: tuple[str, ...]
    zones: tuple[Zone, ...]
    target: int
    criteria: Criteria
    synonyms_on: bool


class InvalidRequest(ValueError):
    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Demande de campagne incomplète.")
        self.errors = errors


def validate_request(raw: RawRequest) -> CampaignRequest:
    """Refuse une demande incomplète en disant quoi corriger, champ par champ."""
    name = raw.name.strip()
    trades = tuple(t.strip() for t in raw.trades if t.strip())
    errors: dict[str, str] = {}
    if not name:
        errors["name"] = "Donnez un nom à la campagne."
    if not trades:
        errors["trades"] = "Indiquez au moins un métier."
    if not raw.zones:
        errors["zones"] = "Indiquez au moins une ville, un département ou un rayon."
    elif any(
        isinstance(z, RadiusZone) and not 1 <= z.radius_km <= MAX_RADIUS_KM for z in raw.zones
    ):
        errors["zones"] = "Choisissez un rayon entre 1 et 50 km."
    if not 1 <= raw.target <= MAX_TARGET:
        errors["target"] = "Choisissez entre 1 et 200 prospects."
    if errors:
        raise InvalidRequest(errors)
    return CampaignRequest(
        name, trades, tuple(raw.zones), raw.target, raw.criteria, raw.synonyms_on
    )
