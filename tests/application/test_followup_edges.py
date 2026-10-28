"""C77, C98, C108 : cas limites des programmations et des rappels."""

from datetime import timedelta

import pytest
from sqlalchemy import Engine

from prospection.application.call_actions import finish_action, schedule
from prospection.application.campaign_end import after_campaign
from prospection.application.reminders import (
    InvalidReminders,
    change_reminders,
    remind_due_actions,
)
from prospection.application.schedules import (
    InvalidSchedule,
    add_schedule,
    delete_schedule,
    run_due_schedule,
    schedule_screen,
)
from prospection.domain.stop_reasons import STOPPED_BY_YOU, budget_reached
from prospection.storage.alerts import unseen_alerts
from prospection.storage.campaigns import set_status
from tests.application.test_call_tracking import PARIS, add
from tests.application.test_followup import WEDNESDAY, _template
from tests.storage.test_campaigns import PLACE

THURSDAY = WEDNESDAY + timedelta(days=1)


def test_C77_same_schedule_saved_once(campaign_db: Engine) -> None:
    _template(campaign_db)
    add_schedule(campaign_db, "Créations 69", "3", "13", WEDNESDAY, PARIS)
    add_schedule(campaign_db, "Créations 69", "3", "13", WEDNESDAY, PARIS)  # double appui
    assert len(schedule_screen(campaign_db)[0]) == 1
    with pytest.raises(InvalidSchedule):
        add_schedule(campaign_db, "Créations 69", "²", "13", WEDNESDAY, PARIS)


def test_C98_unreadable_template_alerts_and_waits_a_week(campaign_db: Engine) -> None:
    _template(campaign_db)
    add_schedule(campaign_db, "Créations 69", "3", "13", WEDNESDAY, PARIS)
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("UPDATE campaign_templates SET request_json = '{}'")
    assert run_due_schedule(campaign_db, THURSDAY, PARIS)
    assert not run_due_schedule(campaign_db, THURSDAY, PARIS)  # pas de boucle
    with campaign_db.connect() as conn:
        [alert] = unseen_alerts(conn)
    assert "non lancée" in alert.message


def _finished(engine: Engine, reason: str) -> None:
    _template(engine)
    add_schedule(engine, "Créations 69", "3", "13", WEDNESDAY, PARIS)
    run_due_schedule(engine, THURSDAY, PARIS)
    delete_schedule(engine, 1)  # supprimée pendant que la campagne tourne
    with engine.begin() as conn:
        set_status(conn, 1, "done", THURSDAY, reason)
    after_campaign(engine, 1, THURSDAY)


def test_C98_failure_reported_even_if_schedule_deleted(campaign_db: Engine) -> None:
    _finished(campaign_db, budget_reached(0, 0, 3))
    with campaign_db.connect() as conn:
        assert [a.kind for a in unseen_alerts(conn)] == ["echec"]


def test_C98_stop_asked_by_me_is_not_a_failure(campaign_db: Engine) -> None:
    _finished(campaign_db, STOPPED_BY_YOU)
    with campaign_db.connect() as conn:
        assert unseen_alerts(conn) == []


def test_C108_moved_or_done_action_retires_its_alert(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    schedule(campaign_db, pid, "rappeler", "2026-10-28", "14:30", WEDNESDAY, PARIS)
    remind_due_actions(campaign_db, WEDNESDAY + timedelta(minutes=20), PARIS)
    schedule(campaign_db, pid, "rappeler", "2026-10-29", "", WEDNESDAY, PARIS)  # déplacée
    remind_due_actions(campaign_db, WEDNESDAY + timedelta(minutes=21), PARIS)
    with campaign_db.connect() as conn:
        assert unseen_alerts(conn) == []
        action_id = conn.exec_driver_sql("SELECT max(id) FROM prospect_actions").scalar_one()
    remind_due_actions(campaign_db, THURSDAY, PARIS)
    finish_action(campaign_db, action_id, THURSDAY)
    remind_due_actions(campaign_db, THURSDAY + timedelta(minutes=1), PARIS)
    with campaign_db.connect() as conn:
        assert unseen_alerts(conn) == []
    with pytest.raises(InvalidReminders):
        change_reminders(campaign_db, "²", "8")
