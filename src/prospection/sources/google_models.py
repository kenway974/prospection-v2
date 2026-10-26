"""Réponse de Google Places (New) : modèles de validation et conversion en Place."""

import re

from pydantic import BaseModel

from prospection.domain.place import PhotoOwnership, Place, clip, web_link
from prospection.domain.trades import normalize


class _Text(BaseModel):
    text: str


class _LatLng(BaseModel):
    latitude: float
    longitude: float


class _Hours(BaseModel):
    weekdayDescriptions: list[str] = []


class _Author(BaseModel):
    displayName: str = ""


class _Photo(BaseModel):
    authorAttributions: list[_Author] = []


class _Component(BaseModel):
    shortText: str = ""
    longText: str = ""
    types: list[str] = []


class ApiPlace(BaseModel):
    id: str
    displayName: _Text
    formattedAddress: str = ""
    location: _LatLng | None = None
    types: list[str] = []
    primaryType: str | None = None
    businessStatus: str | None = None
    nationalPhoneNumber: str | None = None
    internationalPhoneNumber: str | None = None
    websiteUri: str | None = None
    rating: float | None = None
    userRatingCount: int = 0
    regularOpeningHours: _Hours | None = None
    googleMapsUri: str | None = None
    photos: list[_Photo] = []
    addressComponents: list[_Component] = []


def _ownership(api: ApiPlace) -> PhotoOwnership:
    if not api.photos:
        return "inconnu"
    own = normalize(api.displayName.text)
    authors = {normalize(a.displayName) for p in api.photos for a in p.authorAttributions}
    return "probable propriétaire" if own in authors else "clients seulement"


def _component(api: ApiPlace, kind: str) -> str | None:
    found = next((c for c in api.addressComponents if kind in c.types), None)
    return clip(found.shortText or found.longText, 60) if found else None


def _country(api: ApiPlace) -> str | None:
    """Code ISO à deux lettres seulement : un nom long (« Belgique ») ne se compare pas."""
    code = _component(api, "country")
    return code if code and re.fullmatch(r"[A-Z]{2}", code) else None


def to_place(api: ApiPlace) -> Place:
    hours = api.regularOpeningHours.weekdayDescriptions if api.regularOpeningHours else []
    return Place(
        place_id=clip(api.id, 200) or "",
        name=clip(api.displayName.text) or "",
        address=clip(api.formattedAddress) or "",
        lat=api.location.latitude if api.location else None,
        lon=api.location.longitude if api.location else None,
        types=tuple(clip(t, 60) or "" for t in api.types[:20]),
        primary_type=clip(api.primaryType),
        business_status=clip(api.businessStatus),
        phone=clip(api.internationalPhoneNumber or api.nationalPhoneNumber),
        website=web_link(api.websiteUri),
        rating=api.rating,
        review_count=api.userRatingCount,
        opening_hours=tuple(clip(h) or "" for h in hours[:7]),
        maps_url=web_link(api.googleMapsUri),
        photo_count=len(api.photos),
        owner_photo_estimate=_ownership(api),
        country=_country(api),
        admin_area=_component(api, "administrative_area_level_1"),
    )
