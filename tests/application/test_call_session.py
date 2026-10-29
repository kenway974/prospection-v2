"""C61, C109, C120 : liste triée, session d'appel figée et reprise."""

import dataclasses

import pytest
from sqlalchemy import Engine

from prospection.application.call_actions import record_result, today_screen
from prospection.application.prospect_card import UnknownProspect, card
from prospection.application.prospect_listing import prospect_list, start_session
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import PARIS, add
from tests.storage.test_campaigns import PLACE


def three(engine: Engine, *names: str) -> list[int]:
    places = [dataclasses.replace(PLACE, place_id=f"p{n}", name=v) for n, v in enumerate(names)]
    return add(engine, *places)


def test_C109_queue_frozen_when_calls_change_statuses(campaign_db: Engine) -> None:
    first, second, third = three(campaign_db, "A", "B", "C")
    assert start_session(campaign_db, "à appeler", "", "trouves", NOW) == first
    record_result(campaign_db, first, "pas joint", NOW)  # sort du filtre « à appeler »
    shown = card(campaign_db, second, NOW, PARIS, in_session=True)
    assert (shown.position, shown.total, shown.previous_id, shown.next_id) == (2, 3, first, third)
    record_result(campaign_db, second, "intéressé", NOW)
    again = card(campaign_db, second, NOW, PARIS, in_session=True)
    assert (again.position, again.total) == (2, 3)
    resume = today_screen(campaign_db, NOW, PARIS).resume
    assert resume is not None and (resume.prospect_id, resume.position, resume.name) == (
        second,
        2,
        "B",
    )


def test_C109_card_opened_outside_session_leaves_it_alone(campaign_db: Engine) -> None:
    first, _, third = three(campaign_db, "A", "B", "C")
    start_session(campaign_db, None, "", "trouves", NOW)
    shown = card(campaign_db, third, NOW, PARIS)  # depuis Aujourd'hui ou la liste
    assert shown.position is None
    resume = today_screen(campaign_db, NOW, PARIS).resume
    assert resume is not None and resume.prospect_id == first


def test_C61_sorted_by_name_or_city(campaign_db: Engine) -> None:
    ids = three(campaign_db, "Zola Cuisines", "atelier Bois", "Martin")
    by_name = [r.data["name"] for r in prospect_list(campaign_db, None, "", "nom").rows]
    assert by_name == ["atelier Bois", "Martin", "Zola Cuisines"]
    assert start_session(campaign_db, None, "", "nom", NOW) == ids[1]


def test_C120_counts_follow_the_search(campaign_db: Engine) -> None:
    first, _, _ = three(campaign_db, "Cuisines Martin", "Atelier", "Martin Frères")
    record_result(campaign_db, first, "intéressé", NOW)
    assert prospect_list(campaign_db, None, "atelier", "trouves").counts == {"à appeler": 1}
    assert prospect_list(campaign_db, None, "a\x00b", "trouves").rows == []  # NUL sans erreur


def test_unknown_prospect(campaign_db: Engine) -> None:
    with pytest.raises(UnknownProspect):
        card(campaign_db, 999, NOW, PARIS)
