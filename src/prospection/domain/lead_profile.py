"""Profil du lead gardé à l'envoi d'un mail d'audit (C162) : des catégories lisibles, pour
savoir quels leads mènent à une conversation. Rien de personnel (métier, ville, tranches)."""

from collections.abc import Sequence
from datetime import date

from prospection.domain.site_guess import address_city


def _band(value: float, bands: Sequence[tuple[float, str]], below: str) -> str:
    return next((label for floor, label in bands if value >= floor), below)


def _age(created: date | None, today: date) -> str:
    if created is None:
        return "inconnue"
    years = (today - created).days / 365.25
    return _band(years, ((10, "plus de 10 ans"), (5, "5 à 10 ans"), (1, "1 à 5 ans")),
                 "moins d'un an")  # fmt: skip


def lead_profile(
    keywords: Sequence[str], address: str, has_site: bool, rating: float | None, reviews: int,
    score: int, created: date | None, form: str | None, today: date,
) -> dict[str, str]:  # fmt: skip
    rating_band = "sans note" if rating is None else _band(
        rating, ((4.5, "4,5 et plus"), (4.0, "4 à 4,5")), "moins de 4")  # fmt: skip
    return {
        "métier": keywords[0] if keywords else "inconnu",
        "ville": address_city(address) or "inconnue",
        "site": "avec site" if has_site else "sans site",
        "note Google": rating_band,
        "avis Google": _band(reviews, ((50, "50 et plus"), (10, "10 à 49")), "moins de 10"),
        "score": _band(score, ((70, "70 et plus"), (40, "40 à 69")), "moins de 40"),
        "ancienneté": _age(created, today),
        "formulaire": form or "inconnu",
    }
