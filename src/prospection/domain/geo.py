"""Distance entre deux points (rayon autour d'une ville, C13)."""

import math

EARTH_RADIUS_M = 6_371_000


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance à vol d'oiseau (formule de haversine), en mètres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi, d_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
