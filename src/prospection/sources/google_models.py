"""Réponse de Google Places (New) : modèles de validation et conversion en Place."""

from pydantic import BaseModel

from prospection.domain.place import PhotoOwnership, Place, clip
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


def _ownership(api: ApiPlace) -> PhotoOwnership:
    if not api.photos:
        return "inconnu"
    own = normalize(api.displayName.text)
    authors = {normalize(a.displayName) for p in api.photos for a in p.authorAttributions}
    return "probable propriétaire" if own in authors else "clients seulement"


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
        website=clip(api.websiteUri),
        rating=api.rating,
        review_count=api.userRatingCount,
        opening_hours=tuple(clip(h) or "" for h in hours[:7]),
        maps_url=clip(api.googleMapsUri),
        photo_count=len(api.photos),
        owner_photo_estimate=_ownership(api),
    )
