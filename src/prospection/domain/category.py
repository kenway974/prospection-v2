"""Le métier est-il confirmé par le nom ou les catégories Google ? (C23)

Repris de prospection-bot/trades.py (530ba12, category_verdict), relu : une
catégorie inconnue ne fait jamais exclure, elle fait marquer « à vérifier ».
Seule une catégorie clairement hors métier exclut, et seulement pour le bâtiment.
"""

from typing import Literal

from prospection.domain.place import Place
from prospection.domain.trades import Trade, normalize

GENERIC_TYPES = {"point_of_interest", "establishment", "store", "premise"}
NEVER_BUILDING_TYPES = {
    "restaurant", "food", "cafe", "bar", "meal_takeaway", "meal_delivery", "bakery",
    "school", "primary_school", "secondary_school", "university", "lodging", "night_club",
    "gym", "beauty_salon", "hair_care", "doctor", "dentist", "hospital", "pharmacy", "bank",
    "insurance_agency", "real_estate_agency", "car_dealer", "car_repair", "supermarket",
}  # fmt: skip
OTHER_TRADE_TYPES = {
    "electrician", "plumber", "roofing_contractor", "painter", "locksmith", "moving_company",
    "car_repair", "car_wash", "storage",
}  # fmt: skip

Category = tuple[Literal["ok", "check", "exclude"], str]


def _has_word(name: str, words: tuple[str, ...]) -> bool:
    padded = f" {normalize(name)} "
    return any(f" {normalize(word)} " in padded for word in words)


def category_verdict(place: Place, trade: Trade) -> Category:
    specific = {t for t in place.types if t not in GENERIC_TYPES}
    if _has_word(place.name, trade.off_target_name_words):
        return "exclude", "nom"
    if trade.family == "batiment" and specific & NEVER_BUILDING_TYPES:
        return "exclude", ", ".join(sorted(specific & NEVER_BUILDING_TYPES))
    if _has_word(place.name, trade.name_words) or specific & trade.maps_types:
        return "ok", ""
    if trade.family == "batiment" and specific and specific <= OTHER_TRADE_TYPES:
        return "exclude", ", ".join(sorted(specific))
    return "check", f"Métier « {trade.label} » non confirmé"
