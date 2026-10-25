"""Établissement trouvé sur Google Maps (C42, C43), après validation."""

from dataclasses import dataclass
from typing import Literal

MAX_TEXT = 300

PhotoOwnership = Literal["probable propriétaire", "clients seulement", "inconnu"]


@dataclass(frozen=True)
class Circle:
    lat: float
    lon: float
    radius_m: float


@dataclass(frozen=True)
class Place:
    place_id: str
    name: str
    address: str
    lat: float | None
    lon: float | None
    types: tuple[str, ...]
    primary_type: str | None
    business_status: str | None
    phone: str | None
    website: str | None
    rating: float | None
    review_count: int
    opening_hours: tuple[str, ...]
    maps_url: str | None
    photo_count: int
    owner_photo_estimate: PhotoOwnership


def clip(text: str | None) -> str | None:
    return None if text is None else text[:MAX_TEXT]
