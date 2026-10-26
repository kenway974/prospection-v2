"""C11, C24, C26, C125 : source « entreprises récemment créées »."""

import pytest

from prospection.domain.campaign_request import (
    CityZone,
    DepartmentZone,
    InvalidRequest,
    RawRequest,
    validate_request,
)
from prospection.domain.criteria import Criteria
from prospection.domain.registry import workforce_ok

LYON = CityZone("Lyon", "69123", 45.76, 4.83)


def raw(zones: list[object], sources: tuple[str, ...], days: int = 90) -> RawRequest:
    criteria = Criteria(created_within_days=days)
    return RawRequest("Test", ["cuisiniste"], zones, 10, criteria, True, sources)  # type: ignore[arg-type]


def test_C11_both_sources_kept() -> None:
    request = validate_request(raw([LYON], ("google", "registre")))
    assert request.sources == ("google", "registre")


def test_C11_a_source_is_required() -> None:
    with pytest.raises(InvalidRequest) as error:
        validate_request(raw([LYON], ()))
    assert error.value.errors["sources"] == "Choisissez au moins une source."


@pytest.mark.parametrize(
    ("zone", "start"),
    [(DepartmentZone("WLG", "Province de Liège", "BE"), "Belgique : pas de registre"),
     (DepartmentZone("VD", "Canton de Vaud", "CH"), "Suisse : le registre Zefix"),
     (CityZone("Monaco", "", 43.73, 7.42, "MC"), "Monaco : pas d'accès ouvert")],
)  # fmt: skip
def test_C125_registry_outside_france_says_why(zone: object, start: str) -> None:
    with pytest.raises(InvalidRequest) as error:
        validate_request(raw([zone], ("registre",)))
    assert error.value.errors["sources"].startswith(start)
    assert "Google Maps" in error.value.errors["sources"]


def test_C24_creation_window_bounded() -> None:
    with pytest.raises(InvalidRequest) as error:
        validate_request(raw([LYON], ("registre",), days=0))
    assert error.value.errors["days"] == "Choisissez entre 1 et 365 jours."


def test_C26_workforce_at_most() -> None:
    assert workforce_ok("NN", "01") and workforce_ok("01", "01") and workforce_ok(None, "01")
    assert not workforce_ok("03", "01")
    assert workforce_ok("53", None)
