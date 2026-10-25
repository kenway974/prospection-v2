"""Demande de campagne et sa validation (C10 à C14, C17)."""

from collections.abc import Iterable
from dataclasses import dataclass

from prospection.domain.criteria import Criteria
from prospection.domain.trades import normalize

MAX_TARGET = 200
MAX_RADIUS_KM = 50


def _department(insee_code: str) -> str:
    return insee_code[:3] if insee_code.startswith("97") else insee_code[:2]


@dataclass(frozen=True)
class CityZone:
    name: str
    code: str  # code INSEE en France ; ailleurs, région ISO 3166-2 sans le pays (« GE »)
    lat: float
    lon: float
    country: str = "FR"

    @property
    def label(self) -> str:
        if self.country == "FR":
            return f"{self.name} ({_department(self.code)})"
        return (
            f"{self.name} ({self.country}-{self.code})"
            if self.code
            else f"{self.name} ({self.country})"
        )


@dataclass(frozen=True)
class RadiusZone:
    city: CityZone
    radius_km: int

    @property
    def label(self) -> str:
        return f"{self.radius_km} km autour de {self.city.label}"


@dataclass(frozen=True)
class DepartmentZone:
    """Département (France), province (Belgique) ou canton (Suisse, Luxembourg)."""

    code: str
    name: str
    country: str = "FR"

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code if self.country == 'FR' else self.country})"


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


def _unique(trades: Iterable[str]) -> tuple[str, ...]:
    kept: dict[str, str] = {}
    for trade in trades:
        kept.setdefault(normalize(trade), trade)
    return tuple(kept.values())


def _plausible(zone: Zone) -> bool:
    city = zone.city if isinstance(zone, RadiusZone) else zone
    if isinstance(city, DepartmentZone):
        return True
    return -90 <= city.lat <= 90 and -180 <= city.lon <= 180


def validate_request(raw: RawRequest) -> CampaignRequest:
    """Refuse une demande incomplète en disant quoi corriger, champ par champ."""
    name = raw.name.strip()
    trades = _unique(t.strip() for t in raw.trades if normalize(t))
    zones = tuple(dict.fromkeys(raw.zones))  # une zone en double serait payée deux fois
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
    elif not all(_plausible(z) for z in zones):
        errors["zones"] = "Choisissez la commune dans la liste."
    if not 1 <= raw.target <= MAX_TARGET:
        errors["target"] = "Choisissez entre 1 et 200 prospects."
    if errors:
        raise InvalidRequest(errors)
    return CampaignRequest(name, trades, zones, raw.target, raw.criteria, raw.synonyms_on)
