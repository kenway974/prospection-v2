"""C122 : villes, provinces et cantons de Belgique, Suisse, Luxembourg et Monaco."""

from prospection.domain.campaign_request import CityZone, DepartmentZone
from prospection.domain.foreign_zones import (
    countries,
    find_foreign_cities,
    find_region,
    postal_region,
)


def test_C122_five_countries_france_first() -> None:
    assert list(countries()) == ["FR", "BE", "CH", "LU", "MC"]
    assert countries()["CH"] == "Suisse"


def test_C122_city_found_by_its_french_name() -> None:
    [brussels] = find_foreign_cities("bruxelles", "BE")
    assert brussels == CityZone("Bruxelles", "BRU", 50.8505, 4.3488, "BE")
    assert brussels.label == "Bruxelles (BE-BRU)"
    assert find_foreign_cities("Genève", "CH")[0].label == "Genève (CH-GE)"
    assert find_foreign_cities("Monaco", "MC")[0].label == "Monaco (MC)"


def test_C122_unknown_or_wrong_country_gives_nothing() -> None:
    assert find_foreign_cities("Genève", "BE") == []
    assert find_foreign_cities("", "CH") == []


def test_C122_city_prefix_lists_a_few_choices() -> None:
    found = find_foreign_cities("Saint", "CH")
    assert 1 < len(found) <= 10 and all(c.name.startswith("Saint") for c in found)


def test_C122_province_or_canton_by_name_or_code() -> None:
    liege = DepartmentZone("WLG", "Province de Liège", "BE")
    assert find_region("liège", "BE") == liege and find_region("WLG", "BE") == liege
    assert find_region("Vaud", "CH") == DepartmentZone("VD", "Canton de Vaud", "CH")
    assert find_region("Mersch", "LU") == DepartmentZone("ME", "Canton de Mersch", "LU")
    assert find_region("Vaud", "BE") is None and find_region("Monaco", "MC") is None


def test_C123_belgian_province_from_postal_code() -> None:
    assert postal_region("Rue Léopold 1, 4000 Liège, Belgique", "BE") == "WLG"
    assert postal_region("Grand-Place 1, 1000 Bruxelles", "BE") == "BRU"
    assert postal_region("Markt 1, 3000 Leuven", "BE") == "VBR"
    assert postal_region("Rue du Rhône 1, 1204 Genève", "CH") is None
