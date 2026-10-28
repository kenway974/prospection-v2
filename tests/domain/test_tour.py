"""C113, C114 : ordre de tournée, itinéraire Google Maps, « ouvert maintenant »."""

from datetime import datetime
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from prospection.domain.opening import open_now
from prospection.domain.tour import Stop, order_tour, route_links

START = (45.7640, 4.8357)  # Lyon, place Bellecour
FAR = Stop(3, 45.7800, 4.8500)
NEAR = Stop(1, 45.7650, 4.8360)
MID = Stop(2, 45.7700, 4.8400)


def test_C114_nearest_neighbour_from_my_position() -> None:
    assert [s.id for s in order_tour(START, [FAR, NEAR, MID])] == [1, 2, 3]
    assert order_tour(START, []) == []


def test_C114_walking_route_links_split_into_legs() -> None:
    stops = [Stop(i, 45.76 + i / 1000, 4.83) for i in range(12)]
    links = route_links(START, stops, max_waypoints=9)
    assert len(links) == 2  # 12 arrêts : 9 étapes + destination, puis la suite
    first = parse_qs(urlsplit(links[0]).query)
    assert urlsplit(links[0]).netloc == "www.google.com" and first["travelmode"] == ["walking"]
    assert first["origin"] == ["45.764,4.8357"] and len(first["waypoints"][0].split("|")) == 9
    second = parse_qs(urlsplit(links[1]).query)
    assert second["origin"] == [first["destination"][0]]  # le tronçon suivant repart d'où l'on est


PARIS = ZoneInfo("Europe/Paris")
HOURS = ("lundi: 08:00\u201312:00, 14:00\u201318:00", "mardi: Fermé", "mercredi: Ouvert 24h/24")


def test_C113_open_now_read_from_google_hours() -> None:
    monday = datetime(2026, 10, 26, tzinfo=PARIS)
    assert open_now(HOURS, monday.replace(hour=9)) is True
    assert open_now(HOURS, monday.replace(hour=13)) is False
    assert open_now(HOURS, monday.replace(hour=14, minute=30)) is True
    assert open_now(HOURS, datetime(2026, 10, 27, 10, tzinfo=PARIS)) is False  # mardi fermé
    assert open_now(HOURS, datetime(2026, 10, 28, 3, tzinfo=PARIS)) is True  # 24h/24
    assert open_now(HOURS, datetime(2026, 10, 29, 10, tzinfo=PARIS)) is None  # jeudi inconnu
    assert open_now((), monday) is None


def test_C113_open_now_slots_past_midnight() -> None:
    """Un créneau qui passe minuit compte la veille au soir et le lendemain avant la fin."""
    late = ("dimanche: 18:00\u201302:00", "lundi: Fermé", "mardi: 18:00\u201302:00")
    assert open_now(late, datetime(2026, 10, 26, 1, tzinfo=PARIS)) is True  # lundi 1 h
    assert open_now(late, datetime(2026, 10, 27, 1, tzinfo=PARIS)) is False  # mardi 1 h
    assert open_now(late, datetime(2026, 10, 27, 19, tzinfo=PARIS)) is True
    midnight = ("lundi: 08:00\u201324:00",)
    assert open_now(midnight, datetime(2026, 10, 26, 23, 59, 30, tzinfo=PARIS)) is True


def test_C114_mobile_browser_limit_by_default() -> None:
    """Liens Google Maps : 3 étapes au plus dans un navigateur mobile."""
    stops = [Stop(i, 45.76 + i / 1000, 4.83) for i in range(5)]
    assert len(route_links(START, stops)) == 2
