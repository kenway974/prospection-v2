"""C77, C78, C108 : la tâche de fond lance les programmations et prévient des relances."""

from datetime import timedelta

from sqlalchemy import Engine

from prospection.application.call_actions import schedule
from prospection.application.schedules import add_schedule
from prospection.storage.alerts import unseen_alerts
from prospection.storage.templates import save_template
from prospection.worker import Worker
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place, pages, request
from tests.fake_http import fake_client


def test_C77_C78_C108_worker_runs_schedules_and_reminders(campaign_db: Engine) -> None:
    with campaign_db.begin() as conn:
        save_template(conn, "Lundi", request(target=2))
    add_schedule(campaign_db, "Lundi", str(NOW.weekday()), "0", NOW - timedelta(days=1), "UTC")
    client, _ = fake_client(pages([api_place(1), api_place(2)]))
    worker = Worker(campaign_db, BOX, client, PRICING, now=lambda: NOW, timezone="UTC")
    assert worker.work_once() is True  # la programmation lance la campagne
    assert worker.work_once() is True  # qui va jusqu'au bout
    with campaign_db.connect() as conn:
        assert [a.kind for a in unseen_alerts(conn)] == ["nouveaux"]
    with campaign_db.connect() as conn:
        pid = conn.exec_driver_sql("SELECT min(id) FROM prospects").scalar_one()
    schedule(campaign_db, pid, "passer", NOW.date().isoformat(), "", NOW, "UTC")
    worker.next_reminders = NOW
    worker.work_once()
    with campaign_db.connect() as conn:
        assert {a.kind for a in unseen_alerts(conn)} == {"nouveaux", "relance"}
