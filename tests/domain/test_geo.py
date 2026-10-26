"""C13 : distance pour le rayon autour d'une ville."""

from prospection.domain.geo import distance_m


def test_lyon_to_villeurbanne_about_4_km() -> None:
    assert 3_000 < distance_m(45.764, 4.836, 45.767, 4.880) < 4_000


def test_same_point_is_zero() -> None:
    assert distance_m(45.0, 4.0, 45.0, 4.0) == 0
