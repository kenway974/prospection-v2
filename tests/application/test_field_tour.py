"""C113 à C115 : recherche terrain autour de moi, tournée, statut en un geste."""

import dataclasses
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from prospection.application.campaigns import progress
from prospection.application.field_tour import FieldSearch, field_tour, mark_stop, start_field
from prospection.application.prospect_card import card
from prospection.domain.criteria import Verdict
from prospection.storage.prospects import insert_prospect
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import PARIS
from tests.storage.test_campaigns import PLACE

SEARCH = FieldSearch(lat=45.764, lon=4.8357, label="Ma position", trades=("boulangerie",),
                     radius_km=1, max_reviews=20, without_site=True, target=15)  # fmt: skip


def with_stops(engine: Engine) -> int:
    campaign_id = start_field(engine, SEARCH, NOW)
    week = ("lundi", "mardi", "mercredi", "jeudi", "vendredi")
    hours = (*(f"{day}: 08:00-18:00" for day in week), "samedi: Fermé", "dimanche: Fermé")
    with engine.begin() as conn:
        for n, (lat, lon, opening) in enumerate([(45.78, 4.85, hours), (45.765, 4.836, ()),
                                                 (45.77, 4.84, hours)], 1):  # fmt: skip
            place = dataclasses.replace(PLACE, place_id=f"t{n}", name=f"Boutique {n}", lat=lat,
                                        lon=lon, opening_hours=opening)  # fmt: skip
            insert_prospect(conn, campaign_id, place, "boulangerie", Verdict(True, (), ()), NOW)
    return campaign_id


def test_C113_field_search_is_a_campaign_around_me(campaign_db: Engine) -> None:
    campaign_id = start_field(campaign_db, SEARCH, NOW)
    state = progress(campaign_db, campaign_id)
    assert state.status == "queued" and state.name.startswith("Terrain")


def test_C114_stops_in_walking_order_with_route(campaign_db: Engine) -> None:
    campaign_id = with_stops(campaign_db)
    tour = field_tour(campaign_db, campaign_id, NOW, PARIS, open_only=False)
    assert [s.data["name"] for s in tour.stops] == ["Boutique 2", "Boutique 3", "Boutique 1"]
    assert len(tour.links) == 1 and "travelmode=walking" in tour.links[0]


def test_C113_open_now_filter(campaign_db: Engine) -> None:
    campaign_id = with_stops(campaign_db)
    saturday = datetime(2026, 10, 31, 10, tzinfo=ZoneInfo(PARIS))
    weekday = datetime(2026, 10, 29, 10, tzinfo=ZoneInfo(PARIS))
    assert field_tour(campaign_db, campaign_id, saturday, PARIS, open_only=True).stops == []
    names = [s.data["name"] for s in field_tour(campaign_db, campaign_id, weekday, PARIS,
                                                 open_only=True).stops]  # fmt: skip
    assert names == ["Boutique 3", "Boutique 1"]  # horaires inconnus : écartés du filtre


def test_C115_one_gesture_in_front_of_the_shop(campaign_db: Engine) -> None:
    campaign_id = with_stops(campaign_db)
    first, second, third = (s.id for s in field_tour(campaign_db, campaign_id, NOW, PARIS,
                                                     open_only=False).stops)  # fmt: skip
    mark_stop(campaign_db, first, "interesse", NOW, PARIS)
    mark_stop(campaign_db, second, "repasser", NOW, PARIS)
    mark_stop(campaign_db, third, "non", NOW, PARIS)
    assert card(campaign_db, first, NOW, PARIS).prospect.status == "intéressé"
    again = card(campaign_db, second, NOW, PARIS)
    assert again.prospect.status == "à rappeler" and again.action is not None
    assert again.action.kind == "passer"
    assert card(campaign_db, third, NOW, PARIS).prospect.status == "pas intéressé"


def test_C113_google_query_is_the_trade_around_my_position(campaign_db: Engine) -> None:
    """Jamais « boulangerie Ma position » ni l'adresse : le cercle suffit à situer."""
    from prospection.application.campaigns import plan_steps
    from prospection.domain.campaign_request import CityZone, RadiusZone

    zone = RadiusZone(CityZone("12 rue de la République, Lyon", "", 45.76, 4.83), 1)
    (step,) = plan_steps(("boulangerie",), [zone], False)
    assert step.query == "boulangerie" and step.restrict_to_bias


def test_C114_stop_without_position_listed_apart(campaign_db: Engine) -> None:
    campaign_id = with_stops(campaign_db)
    with campaign_db.begin() as conn:
        place = dataclasses.replace(PLACE, place_id="t9", name="Sans GPS", lat=None, lon=None)
        insert_prospect(conn, campaign_id, place, "boulangerie", Verdict(True, (), ()), NOW)
    tour = field_tour(campaign_db, campaign_id, NOW, PARIS, open_only=False)
    assert [r.data["name"] for r in tour.unplaced] == ["Sans GPS"]


def test_C114_tour_only_for_field_searches(campaign_db: Engine) -> None:
    import pytest

    from prospection.application.campaigns import UnknownCampaign, create_campaign
    from tests.application.campaign_helpers import request

    campaign_id = create_campaign(campaign_db, request(), NOW)
    with pytest.raises(UnknownCampaign):
        field_tour(campaign_db, campaign_id, NOW, PARIS, open_only=False)
