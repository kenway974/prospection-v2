"""C10 à C14, C17 : une demande de campagne complète, sinon l'app dit pourquoi."""

import pytest

from prospection.domain.campaign_request import (
    CityZone,
    DepartmentZone,
    InvalidRequest,
    RadiusZone,
    RawRequest,
    validate_request,
)
from prospection.domain.criteria import Criteria

LYON = CityZone("Lyon", "69123", 45.76, 4.83)


def raw(**changes: object) -> RawRequest:
    base: dict[str, object] = {
        "name": "Cuisinistes Lyon",
        "trades": ["cuisiniste"],
        "zones": [LYON],
        "target": 20,
        "criteria": Criteria(),
        "synonyms_on": True,
    }
    base.update(changes)
    return RawRequest(**base)  # type: ignore[arg-type]


def errors_of(request: RawRequest) -> dict[str, str]:
    with pytest.raises(InvalidRequest) as error:
        validate_request(request)
    return error.value.errors


def test_C10_C12_C13_C14_valid_request() -> None:
    request = validate_request(raw(trades=[" cuisiniste ", "", "plombier"]))
    assert request.name == "Cuisinistes Lyon"
    assert request.trades == ("cuisiniste", "plombier")
    assert request.zones == (LYON,)
    assert request.target == 20


def test_C17_missing_trade_or_zone_refused_with_reason() -> None:
    errors = errors_of(raw(trades=["  "], zones=[]))
    assert errors == {
        "trades": "Indiquez au moins un métier.",
        "zones": "Indiquez au moins une ville, un département ou un rayon.",
    }


def test_C10_name_required() -> None:
    assert errors_of(raw(name=" "))["name"] == "Donnez un nom à la campagne."


@pytest.mark.parametrize("target", [0, 201])
def test_C14_target_bounds(target: int) -> None:
    assert errors_of(raw(target=target))["target"] == "Choisissez entre 1 et 200 prospects."


def test_C13_radius_and_department_zones() -> None:
    zones = [RadiusZone(LYON, 15), DepartmentZone("974", "La Réunion")]
    assert validate_request(raw(zones=zones)).zones == tuple(zones)


@pytest.mark.parametrize("radius", [0, 51])
def test_C13_radius_bounds(radius: int) -> None:
    assert errors_of(raw(zones=[RadiusZone(LYON, radius)]))["zones"] == (
        "Choisissez un rayon entre 1 et 50 km."
    )


def test_zone_labels() -> None:
    assert LYON.label == "Lyon (69)"
    assert RadiusZone(LYON, 15).label == "15 km autour de Lyon (69)"
    assert DepartmentZone("974", "La Réunion").label == "La Réunion (974)"


def test_C10_C13_repeated_trades_and_zones_kept_once() -> None:
    rhone = DepartmentZone("69", "Rhône")
    request = validate_request(
        raw(trades=["cuisiniste", " Cuisiniste ", "fleuriste"], zones=[LYON, rhone, LYON, rhone])
    )
    assert request.trades == ("cuisiniste", "fleuriste")
    assert request.zones == (LYON, rhone)


@pytest.mark.parametrize(("lat", "lon"), [(999.0, 4.8), (45.7, -181.0)])
def test_C13_impossible_coordinates_refused(lat: float, lon: float) -> None:
    with pytest.raises(InvalidRequest) as error:
        validate_request(raw(zones=[CityZone("Lyon", "69123", lat, lon)]))
    assert error.value.errors["zones"] == "Choisissez la commune dans la liste."
