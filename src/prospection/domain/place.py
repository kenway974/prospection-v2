"""Établissement trouvé sur Google Maps (C42, C43), après validation."""

import re
from dataclasses import dataclass
from typing import Literal

MAX_TEXT = 300
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]+")

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


def clip(text: str | None, size: int = MAX_TEXT) -> str | None:
    """Texte externe : sans caractères de contrôle (NUL refusé par la base), espaces réduits."""
    return None if text is None else " ".join(_CONTROL.sub(" ", text).split())[:size]
