"""C108, C77, C78, C98 : rappels, campagnes programmées, alertes."""

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine

from prospection.application.call_actions import schedule
from prospection.application.campaign_end import after_campaign
from prospection.application.reminders import (
    InvalidReminders,
    change_reminders,
    remind_due_actions,
)
from prospection.application.schedules import (
    InvalidSchedule,
    add_schedule,
    run_due_schedule,
    schedule_screen,
)
from prospection.domain.criteria import Verdict
from prospection.domain.stop_reasons import budget_reached, goal_reached
from prospection.storage.alerts import mark_seen, unseen_alerts, unseen_count
from prospection.storage.campaigns import load_campaign, set_status
from prospection.storage.prospects import insert_prospect
from prospection.storage.templates import save_template
from tests.application.campaign_helpers import request
from tests.application.test_call_tracking import PARIS, add
from tests.storage.test_campaigns import PLACE

WEDNESDAY = datetime(2026, 10, 28, 13, 0, tzinfo=UTC)  # 14 h à Paris


def test_C108_one_alert_before_each_follow_up(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    schedule(campaign_db, pid, "rappeler", "2026-10-28", "14:30", WEDNESDAY, PARIS)
    assert remind_due_actions(campaign_db, WEDNESDAY, PARIS) == 0  # 14 h : trop tôt
    later = WEDNESDAY + timedelta(minutes=16)
    assert remind_due_actions(campaign_db, later, PARIS) == 1
    assert remind_due_actions(campaign_db, later, PARIS) == 0  # jamais deux fois
    with campaign_db.connect() as conn:
        [alert] = unseen_alerts(conn)
    assert alert.message == "Rappeler · Atelier · 14:30" and alert.link == f"/prospects/{pid}"


def test_C108_reminder_delay_is_adjustable(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    schedule(campaign_db, pid, "rappeler", "2026-10-28", "15:00", WEDNESDAY, PARIS)
    change_reminders(campaign_db, "60", "7")
    assert remind_due_actions(campaign_db, WEDNESDAY, PARIS) == 1
    with pytest.raises(InvalidReminders):
        change_reminders(campaign_db, "500", "8")
    with pytest.raises(InvalidReminders):
        change_reminders(campaign_db, "15", "24")


def _template(engine: Engine) -> None:
    with engine.begin() as conn:
        save_template(conn, "Créations 69", request())


def test_C77_weekly_campaign_from_a_template(campaign_db: Engine) -> None:
    _template(campaign_db)
    with pytest.raises(InvalidSchedule):
        add_schedule(campaign_db, "Inconnu", "0", "7", WEDNESDAY, PARIS)
    add_schedule(campaign_db, "Créations 69", "0", "7", WEDNESDAY, PARIS)  # chaque lundi, 7 h
    [planned], _ = schedule_screen(campaign_db)
    assert planned.next_run_at == datetime(2026, 11, 2, 6, tzinfo=UTC)
    assert not run_due_schedule(campaign_db, WEDNESDAY, PARIS)
    monday = datetime(2026, 11, 2, 6, 1, tzinfo=UTC)
    assert run_due_schedule(campaign_db, monday, PARIS)
    assert not run_due_schedule(campaign_db, monday, PARIS)  # une seule fois
    [planned], _ = schedule_screen(campaign_db)
    assert planned.next_run_at == datetime(2026, 11, 9, 6, tzinfo=UTC)
    with campaign_db.connect() as conn:
        assert load_campaign(conn, 1).request.name == "Créations 69 · 02/11"


def _scheduled_run(engine: Engine, reason: str, new: int) -> int:
    _template(engine)
    add_schedule(engine, "Créations 69", "3", "13", WEDNESDAY, PARIS)  # jeudi 13 h
    assert run_due_schedule(engine, WEDNESDAY + timedelta(days=1), PARIS)
    with engine.begin() as conn:
        for n in range(new):
            place = dataclasses.replace(PLACE, place_id=f"neuf{n}")
            insert_prospect(conn, 1, place, "cuisiniste", Verdict(True, (), ()), WEDNESDAY)
        set_status(conn, 1, "done", WEDNESDAY, reason)
    after_campaign(engine, 1, WEDNESDAY)
    return 1


def test_C78_alert_when_new_companies_match(campaign_db: Engine) -> None:
    _scheduled_run(campaign_db, goal_reached(2), new=2)
    with campaign_db.connect() as conn:
        [alert] = unseen_alerts(conn)
    assert alert.message == "2 nouvelles entreprises pour « Créations 69 · 29/10 »"
    assert alert.link == "/campagnes/1"


def test_C98_alert_when_a_scheduled_campaign_fails(campaign_db: Engine) -> None:
    _scheduled_run(campaign_db, budget_reached(0, 0, 3), new=0)
    with campaign_db.connect() as conn:
        [alert] = unseen_alerts(conn)
    assert alert.kind == "echec" and "Quota gratuit" in alert.message
    with campaign_db.begin() as conn:
        mark_seen(conn, WEDNESDAY)
        assert unseen_count(conn) == 0


def test_C78_no_alert_for_a_campaign_launched_by_hand(campaign_db: Engine) -> None:
    add(campaign_db, PLACE)
    with campaign_db.begin() as conn:
        set_status(conn, 1, "done", WEDNESDAY, budget_reached(0, 0, 3))
    after_campaign(campaign_db, 1, WEDNESDAY)
    with campaign_db.connect() as conn:
        assert unseen_alerts(conn) == []
