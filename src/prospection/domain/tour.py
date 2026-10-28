"""Tournée terrain : ordre de passage et itinéraire Google Maps (C114).

Ordre : heuristique du plus proche voisin, à vol d'oiseau, calculée ici (gratuite).
Itinéraire : URL officielle de Google Maps (`/maps/dir/?api=1`), à pied ; au-delà de la
limite d'étapes, plusieurs tronçons, chacun repartant de la fin du précédent.
"""

from dataclasses import dataclass
from urllib.parse import urlencode

from prospection.domain.geo import distance_m

# Étapes intermédiaires par lien : 3 au plus dans un navigateur mobile (9 ailleurs),
# d'après la documentation des liens Google Maps (« Maps URLs »).
MAX_WAYPOINTS = 3
DIR_URL = "https://www.google.com/maps/dir/"


@dataclass(frozen=True)
class Stop:
    id: int
    lat: float
    lon: float


def order_tour(start: tuple[float, float], stops: list[Stop]) -> list[Stop]:
    """Toujours vers l'arrêt le plus proche de là où l'on est."""
    left, here, ordered = list(stops), start, []
    while left:
        nearest = min(left, key=lambda s: distance_m(here[0], here[1], s.lat, s.lon))
        left.remove(nearest)
        ordered.append(nearest)
        here = (nearest.lat, nearest.lon)
    return ordered


def _point(lat: float, lon: float) -> str:
    return f"{round(lat, 6)},{round(lon, 6)}"


def route_links(
    start: tuple[float, float], stops: list[Stop], max_waypoints: int = MAX_WAYPOINTS
) -> list[str]:
    links, origin = [], _point(*start)
    for i in range(0, len(stops), max_waypoints + 1):
        leg = stops[i : i + max_waypoints + 1]
        params = {"api": "1", "origin": origin, "destination": _point(leg[-1].lat, leg[-1].lon),
                  "travelmode": "walking"}  # fmt: skip
        if len(leg) > 1:
            params["waypoints"] = "|".join(_point(s.lat, s.lon) for s in leg[:-1])
        links.append(f"{DIR_URL}?{urlencode(params)}")
        origin = params["destination"]
    return links
