"""C102 à C107, C109 : suivre ses appels depuis la fiche."""

import dataclasses
from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import Engine

from prospection.application.call_actions import (
    InvalidInput,
    finish_action,
    record_result,
    save_contact,
    save_note,
    schedule,
    today_screen,
)
from prospection.application.prospect_card import UnknownProspect, card, prospect_list
from prospection.domain.criteria import Verdict
from prospection.domain.place import Place
from prospection.storage.campaigns import create_campaign
from prospection.storage.prospects import insert_prospect
from tests.application.campaign_helpers import NOW, request
from tests.storage.test_campaigns import PLACE, STEPS

PARIS = "Europe/Paris"


def add(engine: Engine, *places: Place) -> list[int]:
    with engine.begin() as conn:
        campaign_id = create_campaign(conn, request(), STEPS, NOW)
        for place in places:
            insert_prospect(conn, campaign_id, place, "cuisiniste", Verdict(True, (), ()), NOW)
    return [r.id for r in prospect_list(engine, None, "").rows]


def three(engine: Engine) -> list[int]:
    places = [dataclasses.replace(PLACE, place_id=f"p{n}", name=f"Prospect {n}") for n in range(3)]
    return add(engine, *places)


def test_C109_card_knows_its_place_in_the_queue_and_is_remembered(campaign_db: Engine) -> None:
    first, second, third = three(campaign_db)
    shown = card(campaign_db, second, None, "", NOW)
    assert (shown.position, shown.total, shown.previous_id, shown.next_id) == (2, 3, first, third)
    resume = today_screen(campaign_db, NOW, PARIS).resume
    assert resume is not None and (resume.prospect_id, resume.position) == (second, 2)


def test_C102_C103_result_recorded_and_callback_proposed(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    record_result(campaign_db, pid, "messagerie", NOW, PARIS)
    shown = card(campaign_db, pid, None, "", NOW)
    assert shown.prospect.status == "messagerie"
    assert shown.action is not None and (shown.action.kind, shown.action.due_date) == (
        "rappeler",
        date(2026, 10, 26),
    )
    with pytest.raises(InvalidInput):
        record_result(campaign_db, pid, "exporté", NOW, PARIS)


def test_C103_C107_scheduled_action_shown_today_then_finished(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    schedule(campaign_db, pid, "rendez-vous", "2026-10-25", "14:30", NOW)
    screen = today_screen(campaign_db, NOW, PARIS)
    assert [(i.kind, i.due_time) for i in screen.agenda.today] == [("rendez-vous", time(14, 30))]
    finish_action(campaign_db, screen.agenda.today[0].id, NOW)
    assert today_screen(campaign_db, NOW, PARIS).agenda.today == []


@pytest.mark.parametrize(
    ("kind", "day", "at", "field"),
    [("partir", "2026-10-25", "", "kind"), ("rappeler", "demain", "", "date"),
     ("rappeler", "2026-10-25", "25:00", "time")],
)  # fmt: skip
def test_C106_invalid_action_refused_field_by_field(
    campaign_db: Engine, kind: str, day: str, at: str, field: str
) -> None:
    [pid] = add(campaign_db, PLACE)
    with pytest.raises(InvalidInput) as error:
        schedule(campaign_db, pid, kind, day, at, NOW)
    assert error.value.field == field


def test_C104_C105_note_and_contact(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    save_note(campaign_db, pid, "  Devis en cours  ", NOW)
    save_contact(campaign_db, pid, "Marie", "06 12 34 56 78", "", NOW)
    shown = card(campaign_db, pid, None, "", NOW)
    assert [n.text for n in shown.notes] == ["Devis en cours"]
    assert shown.prospect.contact[:2] == ("Marie", "+33612345678")
    with pytest.raises(InvalidInput):
        save_note(campaign_db, pid, "   ", NOW)


def test_tel_link_keeps_only_digits_and_plus(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, dataclasses.replace(PLACE, phone='+33 6 12" onclick=x 34'))
    assert card(campaign_db, pid, None, "", NOW).tel == "+3361234"


def test_unknown_prospect(campaign_db: Engine) -> None:
    with pytest.raises(UnknownProspect):
        card(campaign_db, 999, None, "", datetime(2026, 1, 1, tzinfo=UTC))


def test_links_checked_again_when_shown(campaign_db: Engine) -> None:
    """Défense en profondeur (règle 5) : un lien déjà en base est revérifié à l'affichage."""
    evil = dataclasses.replace(
        PLACE, website="javascript:alert(1)", maps_url="https://maps.google.com/?cid=1"
    )
    [pid] = add(campaign_db, evil)
    shown = card(campaign_db, pid, None, "", NOW)
    assert (shown.website, shown.maps_url) == (None, "https://maps.google.com/?cid=1")
