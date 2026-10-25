"""La tâche de fond fait avancer les campagnes et s'arrête proprement."""

import threading

import httpx
from sqlalchemy import Engine, text

from prospection.application.campaign_queue import claim_next
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


def test_C40_stop_signal_mid_campaign_gives_the_campaign_back(campaign_db: Engine) -> None:
    stop = threading.Event()
    serve = pages([api_place(1)], [api_place(2)], [api_place(3)])

    def handler(request: httpx.Request) -> httpx.Response:
        stop.set()  # SIGTERM pendant la première page (déploiement)
        return serve(request)

    client, recorder = fake_client(handler)
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    worker = Worker(campaign_db, BOX, client, PRICING, "Europe/Paris", now=lambda: NOW)
    assert worker.work_once(stop) is True
    assert len(recorder.requests) == 1
    assert progress(campaign_db, campaign_id).found == 1
    assert claim_next(campaign_db, NOW, "suivant") == campaign_id  # reprise immédiate


def test_C40_worker_lets_go_when_another_worker_took_over(campaign_db: Engine) -> None:
    serve = pages([api_place(1)], [api_place(2)], [api_place(3)])

    def handler(request: httpx.Request) -> httpx.Response:
        with campaign_db.begin() as conn:
            conn.execute(text("UPDATE campaigns SET claimed_by = 'autre worker'"))
        return serve(request)

    client, recorder = fake_client(handler)
    create_campaign(campaign_db, request(target=9), NOW)
    worker = Worker(campaign_db, BOX, client, PRICING, "Europe/Paris", now=lambda: NOW)
    assert worker.work_once() is True
    assert len(recorder.requests) == 1
