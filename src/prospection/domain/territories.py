"""Territoires français : pour Google et pour les numéros, l'outre-mer a son propre code pays."""

FRENCH_TERRITORIES = ("FR", "RE", "GP", "MQ", "GF", "YT", "PM", "BL", "MF", "NC", "PF", "WF")


def same_country(found: str, wanted: str) -> bool:
    """La Réunion (RE) est en France ; ailleurs, le code doit être le même."""
    return found in FRENCH_TERRITORIES if wanted == "FR" else found == wanted
