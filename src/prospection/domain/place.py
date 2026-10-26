"""Établissement trouvé sur Google Maps (C42, C43), après validation."""

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

MAX_TEXT = 300
MAX_URL = 2000
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
    country: str | None = None  # code ISO du pays d'après Google (« BE »)
    admin_area: str | None = None  # région administrative d'après Google (canton « VD »…)


def clip(text: str | None, size: int = MAX_TEXT) -> str | None:
    """Texte externe : sans caractères de contrôle (NUL refusé par la base), espaces réduits."""
    return None if text is None else " ".join(_CONTROL.sub(" ", text).split())[:size]


def web_link(url: object) -> str | None:
    """Lien http(s) complet, ou rien : jamais `javascript:` ni lien tronqué (règle 5)."""
    clean = clip(url, MAX_URL + 1) if isinstance(url, str) else None
    if not clean or len(clean) > MAX_URL:
        return None
    parts = urlsplit(clean)
    return clean if parts.scheme in ("http", "https") and parts.netloc else None
