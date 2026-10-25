"""Déduplication (C38) : un établissement n'est traité qu'une fois par campagne."""

from collections.abc import Iterable


def new_places(place_ids: Iterable[str], already_seen: set[str]) -> list[str]:
    """Identifiants pas encore vus, dans l'ordre, sans doublon."""
    seen = set(already_seen)
    fresh = []
    for place_id in place_ids:
        if place_id not in seen:
            seen.add(place_id)
            fresh.append(place_id)
    return fresh
