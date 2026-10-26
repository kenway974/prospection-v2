"""C102 à C106, C109, C120 : suivi des appels en base."""

import dataclasses
from datetime import date, time, timedelta

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from prospection.domain.criteria import Verdict
from prospection.storage.call_tracking import (
    add_note,
    agenda_items,
    complete_action,
    notes,
    open_action,
    plan_action,
    set_call_status,
    update_contact,
)
from prospection.storage.campaigns import create_campaign
from prospection.storage.prospect_list import (
    load_session,
    move_session,
    prospect_ids,
    start_session,
    status_counts,
)
from prospection.storage.prospects import insert_prospect
from tests.storage.test_campaigns import NOW, PLACE, REQUEST, STEPS

QUALIFIED = Verdict(True, (), ())


def prospects(conn: Connection, *names: str) -> list[int]:
    campaign_id = create_campaign(conn, REQUEST, STEPS, NOW)
    for n, name in enumerate(names):
        place = dataclasses.replace(PLACE, place_id=f"p{n}", name=name)
        insert_prospect(
            conn, campaign_id, place, "cuisiniste", QUALIFIED, NOW + timedelta(minutes=n)
        )
    insert_prospect(conn, campaign_id, dataclasses.replace(PLACE, place_id="exclu"), "x",
                    Verdict(False, ("Trop d'avis",), ()), NOW)  # fmt: skip
    return prospect_ids(conn, None, "", "trouves")


def test_C120_only_qualified_listed_with_counts_and_search(conn: Connection) -> None:
    first, second, third = prospects(conn, "Cuisines Martin", "Atelier Bois", "Martin Frères")
    set_call_status(conn, second, "intéressé", NOW)
    assert status_counts(conn, "") == {"à appeler": 2, "intéressé": 1}
    assert prospect_ids(conn, "à appeler", "", "trouves") == [first, third]
    assert prospect_ids(conn, None, "martin", "trouves") == [first, third]
    assert prospect_ids(conn, None, "100%_", "trouves") == []  # caractères spéciaux sans effet


def test_C104_notes_dated_newest_first(conn: Connection) -> None:
    [pid] = prospects(conn, "Cuisines Martin")
    add_note(conn, pid, "Rappeler après 14 h", NOW)
    add_note(conn, pid, "A un devis en cours", NOW + timedelta(hours=1))
    assert [(n.text, n.created_at) for n in notes(conn, pid)] == [
        ("A un devis en cours", NOW + timedelta(hours=1)),
        ("Rappeler après 14 h", NOW),
    ]


def test_C103_one_open_action_replaced_then_completed(conn: Connection) -> None:
    [pid] = prospects(conn, "Cuisines Martin")
    plan_action(conn, pid, "rappeler", date(2026, 10, 26), None, NOW)
    plan_action(conn, pid, "rendez-vous", date(2026, 10, 28), time(14, 30), NOW)
    action = open_action(conn, pid)
    assert action is not None and (action.kind, action.due_time) == ("rendez-vous", time(14, 30))
    assert [(i.prospect_name, i.kind) for i in agenda_items(conn)] == [
        ("Cuisines Martin", "rendez-vous")
    ]
    complete_action(conn, action.id, NOW)
    assert open_action(conn, pid) is None and agenda_items(conn) == []


def test_C103_database_refuses_two_open_actions(conn: Connection) -> None:
    [pid] = prospects(conn, "Cuisines Martin")
    plan_action(conn, pid, "rappeler", date(2026, 10, 26), None, NOW)
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO prospect_actions (prospect_id, kind, due_date, created_at) "
                "VALUES (:pid, 'passer', '2026-10-27', now())"
            ),
            {"pid": pid},
        )


def test_C105_contact_saved(conn: Connection) -> None:
    [pid] = prospects(conn, "Cuisines Martin")
    update_contact(conn, pid, ("Marie Dupont", "+33612345678", None), NOW)
    row = conn.execute(
        text("SELECT contact_name, contact_mobile, contact_email FROM prospects WHERE id = :pid"),
        {"pid": pid},
    ).one()
    assert tuple(row) == ("Marie Dupont", "+33612345678", None)


def test_C109_session_remembered(conn: Connection) -> None:
    first, second = prospects(conn, "A", "B")
    assert load_session(conn) is None
    start_session(conn, [first, second], NOW)
    move_session(conn, second, NOW)
    session = load_session(conn)
    assert session is not None and (session.queue, session.prospect_id) == ([first, second], second)


def test_C103_replanning_twice_quickly_keeps_one_open_action(conn: Connection) -> None:
    [pid] = prospects(conn, "A")
    for day in (26, 27):  # double appui : plus d'erreur d'unicité
        plan_action(conn, pid, "rappeler", date(2026, 10, day), None, NOW)
    action = open_action(conn, pid)
    assert action is not None and action.due_date == date(2026, 10, 27)
