"""Formulaire Terrain : lecture et contrôle des champs (C113)."""

from prospection.application.field_tour import FieldSearch
from prospection.domain.trades import MAX_TRADES, split_trades

FIELD_DEFAULTS = {"metiers": "commerce", "rayon": "1", "avis_max": "20", "nombre": "15"}


def _number(text: str, low: int, high: int) -> int | None:
    value = int(text) if text.strip().isdigit() else None
    return value if value is not None and low <= value <= high else None


def _coordinate(text: str, limit: float) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if -limit <= value <= limit else None


def read_field_form(form: dict[str, str]) -> tuple[FieldSearch | None, dict[str, str]]:
    """La recherche, ou None si la position manque encore (adresse à localiser) ; erreurs."""
    errors = {}
    radius = _number(form.get("rayon", "1"), 1, 5)
    target = _number(form.get("nombre", "15"), 1, 50)
    reviews = form.get("avis_max", "").strip()
    max_reviews = _number(reviews, 0, 10_000) if reviews else None
    if radius is None:
        errors["rayon"] = "Choisissez un rayon entre 1 et 5 km."
    if target is None:
        errors["nombre"] = "Choisissez entre 1 et 50 commerces."
    if reviews and max_reviews is None:
        errors["avis_max"] = "Écrivez un nombre d'avis, ou laissez vide."
    lat, lon = _coordinate(form.get("lat", ""), 90), _coordinate(form.get("lon", ""), 180)
    if errors:
        return None, errors
    if lat is None or lon is None:
        if not form.get("adresse", "").strip():
            return None, {"adresse": "Utilisez votre position, ou écrivez une adresse."}
        return None, {}
    trades = tuple(split_trades(form.get("metiers", ""))[: MAX_TRADES + 1])  # au-delà : refusé
    return FieldSearch(lat, lon, form.get("lieu", "Ma position")[:60] or "Ma position",
                       trades or ("commerce",), radius or 1, max_reviews,
                       form.get("sans_site") == "on", target or 15), {}  # fmt: skip
