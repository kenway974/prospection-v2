"""C102 à C107 : saisies de la fiche d'appel."""

import dataclasses
from datetime import date, time

import pytest
from sqlalchemy import Engine

from prospection.application.call_actions import (
    InvalidInput,
    finish_action,
    record_result,
    reopen_action,
    save_contact,
    save_note,
    schedule,
    today_screen,
)
from prospection.application.prospect_card import card, prospect_list
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
    return [r.id for r in prospect_list(engine, None, "", "trouves").rows]


def test_C102_C103_result_recorded_callback_only_proposed(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    record_result(campaign_db, pid, "messagerie", NOW)
    shown = card(campaign_db, pid, NOW, PARIS)
    assert shown.prospect.status == "messagerie" and shown.action is None
    assert shown.proposal == ("rappeler", date(2026, 10, 26))
    record_result(campaign_db, pid, "intéressé", NOW)  # erreur corrigée : rien d'orphelin
    assert today_screen(campaign_db, NOW, PARIS).agenda.tomorrow == []
    with pytest.raises(InvalidInput):
        record_result(campaign_db, pid, "exporté", NOW)


def test_C103_C107_scheduled_action_shown_finished_then_undone(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    schedule(campaign_db, pid, "rendez-vous", "2026-10-25", "14:30", NOW, PARIS)
    schedule(campaign_db, pid, "rendez-vous", "2026-10-25", "15:00", NOW, PARIS)  # remplace
    screen = today_screen(campaign_db, NOW, PARIS)
    assert [(i.kind, i.due_time) for i in screen.agenda.today] == [("rendez-vous", time(15, 0))]
    action_id = screen.agenda.today[0].id
    assert finish_action(campaign_db, action_id, NOW) is True
    assert finish_action(campaign_db, action_id, NOW) is False  # déjà terminée
    assert today_screen(campaign_db, NOW, PARIS).agenda.today == []
    assert reopen_action(campaign_db, action_id) is True
    assert len(today_screen(campaign_db, NOW, PARIS).agenda.today) == 1


@pytest.mark.parametrize(
    ("kind", "day", "at", "field"),
    [("partir", "2026-10-25", "", "kind"), ("rappeler", "demain", "", "date"),
     ("rappeler", "0001-01-01", "", "date"), ("rappeler", "2031-01-01", "", "date"),
     ("rappeler", "2026-10-25", "25:00", "time")],
)  # fmt: skip
def test_C106_invalid_action_refused_field_by_field(
    campaign_db: Engine, kind: str, day: str, at: str, field: str
) -> None:
    [pid] = add(campaign_db, PLACE)
    with pytest.raises(InvalidInput) as error:
        schedule(campaign_db, pid, kind, day, at, NOW, PARIS)
    assert error.value.field == field


def test_C104_C105_note_and_contact(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    save_note(campaign_db, pid, "  Devis en cours\nRappeler\x00 lundi ", NOW)
    save_contact(campaign_db, pid, "Marie", "06 12 34 56 78", "", NOW)
    shown = card(campaign_db, pid, NOW, PARIS)
    assert [n.text for n in shown.notes] == ["Devis en cours\nRappeler lundi"]
    assert shown.prospect.contact[:2] == ("Marie", "+33612345678")
    with pytest.raises(InvalidInput):
        save_note(campaign_db, pid, "   ", NOW)


@pytest.mark.parametrize(
    ("name", "email", "field"), [("x" * 101, "", "name"), ("", "a" * 250 + "@b.fr", "email")]
)
def test_C106_too_long_contact_refused_not_cut(
    campaign_db: Engine, name: str, email: str, field: str
) -> None:
    [pid] = add(campaign_db, PLACE)
    with pytest.raises(InvalidInput) as error:
        save_contact(campaign_db, pid, name, "", email, NOW)
    assert error.value.field == field


def test_links_checked_again_when_shown(campaign_db: Engine) -> None:
    """Défense en profondeur (règle 5) : un lien déjà en base est revérifié à l'affichage."""
    evil = dataclasses.replace(
        PLACE, website="javascript:alert(1)", maps_url="https://maps.google.com/?cid=1"
    )
    [pid] = add(campaign_db, evil)
    shown = card(campaign_db, pid, NOW, PARIS)
    assert (shown.website, shown.maps_url) == (None, "https://maps.google.com/?cid=1")


def test_tel_link_keeps_only_digits_and_plus(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, dataclasses.replace(PLACE, phone='+33 6 12" onclick=x 34'))
    assert card(campaign_db, pid, NOW, PARIS).tel == "+3361234"
