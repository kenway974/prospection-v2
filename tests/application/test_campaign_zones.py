"""C13 : seuls les établissements de la zone choisie sont gardés."""

from sqlalchemy import Engine

from prospection.application.campaigns import create_campaign, progress
from prospection.domain.campaign_request import (
    CampaignRequest,
    CityZone,
    DepartmentZone,
    RadiusZone,
    Zone,
)
from prospection.domain.criteria import Criteria
from tests.application.campaign_helpers import LYON, NOW, api_place, pages
from tests.application.test_campaign_step import run_all
from tests.fake_http import fake_client


def test_C13_place_outside_radius_excluded(campaign_db: Engine) -> None:
    far = {**api_place(2), "location": {"latitude": 46.5, "longitude": 4.83}}
    client, _ = fake_client(pages([api_place(1), far]))
    radius_request = CampaignRequest(
        "Test", ("cuisiniste",), (RadiusZone(LYON, 15),), 9, Criteria(phone="any"), False
    )
    campaign_id = create_campaign(campaign_db, radius_request, NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.qualified, state.exclusion_counts) == (1, [("Hors zone", 1)])


def test_C13_place_outside_department_excluded(campaign_db: Engine) -> None:
    paris = {**api_place(2), "formattedAddress": "3 rue de Rivoli, 75001 Paris, France"}
    lyon = {**api_place(1), "formattedAddress": "3 rue de la Ré, 69002 Lyon, France"}
    client, _ = fake_client(pages([lyon, paris]))
    rhone = CampaignRequest(
        "Test", ("cuisiniste",), (DepartmentZone("69", "Rhône"),), 9, Criteria(phone="any"), False
    )
    campaign_id = create_campaign(campaign_db, rhone, NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.qualified, state.exclusion_counts) == (1, [("Hors zone", 1)])


def _in(country: str, admin: str = "", address: str = "") -> dict[str, object]:
    components = [{"shortText": country, "longText": country, "types": ["country"]}]
    if admin:
        components.append(
            {"shortText": admin, "longText": admin, "types": ["administrative_area_level_1"]}
        )
    return {"addressComponents": components, "formattedAddress": address}


def _run(campaign_db: Engine, zone: Zone, *places: dict[str, object]) -> list[tuple[str, int]]:
    request = CampaignRequest("T", ("cuisiniste",), (zone,), 9, Criteria(phone="any"), False)
    client, _ = fake_client(pages(list(places)))
    campaign_id = create_campaign(campaign_db, request, NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    return [("qualifiés", state.qualified), *state.exclusion_counts]


def test_C123_place_in_another_country_excluded(campaign_db: Engine) -> None:
    liege = CityZone("Liège", "WLG", 50.6326, 5.5797, "BE")
    belgian = {**api_place(1), **_in("BE"), "location": {"latitude": 50.63, "longitude": 5.57}}
    french = {**api_place(2), **_in("FR"), "location": {"latitude": 50.63, "longitude": 5.57}}
    assert _run(campaign_db, liege, belgian, french) == [("qualifiés", 1), ("Hors zone", 1)]


def test_C123_belgian_province_checked_by_postal_code(campaign_db: Engine) -> None:
    province = DepartmentZone("WLG", "Province de Liège", "BE")
    inside = {**api_place(1), **_in("BE", address="Rue Léopold 1, 4000 Liège, Belgique")}
    brussels = {**api_place(2), **_in("BE", address="Grand-Place 1, 1000 Bruxelles, Belgique")}
    assert _run(campaign_db, province, inside, brussels) == [("qualifiés", 1), ("Hors zone", 1)]


def test_C123_swiss_canton_checked_when_google_names_it(campaign_db: Engine) -> None:
    vaud = DepartmentZone("VD", "Canton de Vaud", "CH")
    lausanne = {**api_place(1), **_in("CH", "VD")}
    geneva = {**api_place(2), **_in("CH", "GE")}
    # nom de canton inconnu : gardé, pas d'exclusion au moindre doute
    unnamed = {**api_place(3), **_in("CH", "Waadt")}
    assert _run(campaign_db, vaud, lausanne, geneva, unnamed) == [
        ("qualifiés", 2),
        ("Hors zone", 1),
    ]


def test_C123_overseas_france_is_france(campaign_db: Engine) -> None:
    reunion = CityZone("Saint-Denis", "97411", -20.88, 55.45)
    place = {**api_place(1), **_in("RE"), "location": {"latitude": -20.88, "longitude": 55.45}}
    lyon_like = {**api_place(2), **_in("FR"), "location": {"latitude": -20.88, "longitude": 55.45}}
    assert _run(campaign_db, reunion, place, lyon_like) == [("qualifiés", 2)]


def test_C123_country_long_name_alone_is_not_trusted(campaign_db: Engine) -> None:
    liege = CityZone("Liège", "WAL", 50.6326, 5.5797, "BE")
    long_only = {
        **api_place(1), "location": {"latitude": 50.63, "longitude": 5.57},
        "addressComponents": [{"shortText": "", "longText": "Belgique", "types": ["country"]}],
    }  # fmt: skip
    assert _run(campaign_db, liege, long_only) == [("qualifiés", 1)]


def test_C123_luxembourg_canton_checked_when_google_names_it(campaign_db: Engine) -> None:
    mersch = DepartmentZone("ME", "Canton de Mersch", "LU")
    inside = {**api_place(1), **_in("LU", "Mersch")}
    diekirch = {**api_place(2), **_in("LU", "Diekirch")}
    assert _run(campaign_db, mersch, inside, diekirch) == [("qualifiés", 1), ("Hors zone", 1)]
