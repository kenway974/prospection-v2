"""Indices de santé de l'entreprise (C112), à partir des données publiques déjà gardées.

Rien d'inventé : « non publié » quand l'information manque, « probable » quand c'est une
estimation. Le rythme des avis demanderait un champ Google payant : il est dit « non
disponible » (budget à 0 €, voir le plan du lot 6).
"""

from prospection.domain.company_card import (
    NON_DIFFUSIBLE,
    NOT_FRENCH,
    NOT_PUBLISHED,
    SURE,
    TO_CONFIRM,
    euros,
    labels,
)
from prospection.domain.signals import Signals, months

_WHY = {
    TO_CONFIRM: "entreprise pas trouvée avec certitude",
    NOT_FRENCH: "registre non consulté (hors France)",
    NON_DIFFUSIBLE: "non diffusé à la demande de l'entreprise",
    SURE: NOT_PUBLISHED,
}
_PHOTOS = {"probable propriétaire": "ajoutées par le propriétaire : probable",
           "clients seulement": "ajoutées par des clients : probable"}  # fmt: skip


def _figures(s: Signals) -> list[tuple[str, str]]:
    company = s.company
    if company is None:  # dire pourquoi, plutôt que « non publié » (rien d'inventé)
        why = _WHY.get(s.registry_status or "", "registre pas encore consulté")
        return [("Chiffre d'affaires", why), ("Effectif", why)]
    staff = labels().effectifs.get(company.workforce or "", NOT_PUBLISHED)
    lines = [("Effectif", staff)]
    if company.finances:
        year, revenue, result = company.finances
        return [(f"Chiffre d'affaires {year}", euros(revenue)), (f"Résultat {year}", euros(result)),
                *lines]  # fmt: skip
    return [("Chiffre d'affaires", NOT_PUBLISHED), *lines]


def _google(s: Signals) -> list[tuple[str, str]]:
    place = s.place
    days = len(place.opening_hours)
    hours = f"publiés sur Google ({days} jour{'s' if days > 1 else ''})" if days else "non publiés"
    rating = f", note {place.rating:.1f}/5".replace(".", ",") if place.rating else ""
    reviews = f"{place.review_count} avis{rating} (rythme non disponible)"
    estimate = _PHOTOS.get(place.owner_photo_estimate)
    photos = f"{place.photo_count} ({estimate})" if estimate else str(place.photo_count)
    return [("Horaires", hours), ("Avis", reviews), ("Photos", photos)]


def health_lines(s: Signals) -> list[tuple[str, str]]:
    age = months(s.age_days) if s.age_days is not None else "non publiée"
    return [*_figures(s), ("Ancienneté", age), *_google(s)]
