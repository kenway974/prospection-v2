"""La tâche de fond fait avancer les campagnes et s'arrête proprement."""

import threading

from sqlalchemy import Engine

from prospection.application.campaigns import create_campaign, progress
from prospection.worker import Worker
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place, pages, request
from tests.fake_http import fake_client


def test_worker_runs_campaign_to_the_end(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1), api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=2), NOW)
    worker = Worker(campaign_db, BOX, client, PRICING, "Europe/Paris", now=lambda: NOW)
    assert worker.work_once() is True
    assert progress(campaign_db, campaign_id).status == "done"
    assert worker.work_once() is False


def test_worker_stops_on_signal(campaign_db: Engine) -> None:
    client, _ = fake_client(pages())
    stop = threading.Event()
    worker = Worker(campaign_db, BOX, client, PRICING, "Europe/Paris", now=lambda: NOW)
    thread = threading.Thread(target=worker.run_forever, args=(stop, 0.01))
    thread.start()
    stop.set()
    thread.join(2)
    assert not thread.is_alive()
