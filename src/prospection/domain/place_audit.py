"""Audit de la fiche Google d'un établissement (C161) : avis, note, horaires, photos, site.

Seulement ce que donne l'API officielle : les réponses du propriétaire aux avis n'y sont pas.
Une entreprise sans fiche Google connue (venue du registre) n'est pas jugée.
"""

from prospection.domain.place import Place
from prospection.domain.site_findings import CRITICAL, MAJOR, MINOR, Finding

MIN_REVIEWS, MIN_RATING, MIN_PHOTOS = 10, 4.0, 5
SIGNIFICANT_REVIEWS = 5  # en dessous, la note ne veut rien dire


def place_findings(place: Place, no_site: bool) -> list[Finding]:
    """`no_site` : aucun vrai site trouvé (ni sur la fiche, ni retrouvé)."""
    if place.place_id.startswith("siren:"):
        return []
    rating = place.rating
    note = f"{rating:.1f}".replace(".", ",") if rating is not None else ""
    checks = [
        (no_site, "no_site", "Pas de site internet", CRITICAL),
        (place.review_count < MIN_REVIEWS, "gmb_few_reviews",
         f"Peu d'avis sur la fiche Google ({place.review_count})", MAJOR),
        (rating is not None and rating < MIN_RATING
         and place.review_count >= SIGNIFICANT_REVIEWS, "gmb_low_rating",
         f"Note Google moyenne ({note}/5)", MAJOR),
        (not place.opening_hours, "gmb_no_hours", "Horaires absents de la fiche Google", MINOR),
        (place.photo_count < MIN_PHOTOS, "gmb_few_photos",
         f"Peu de photos sur la fiche Google ({place.photo_count})", MINOR),
    ]  # fmt: skip
    return [(code, text, weight) for failed, code, text, weight in checks if failed]
