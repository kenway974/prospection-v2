"""La tâche de fond fait avancer les campagnes page par page, à tour de rôle (C40)."""

import itertools
import json
import threading
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import Engine, text

from prospection.application.campaign_queue import claim_next
from prospection.application.campaigns import create_campaign, progress
from prospection.worker import Worker
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place, pages, request
from tests.fake_http import fake_client


def worker_for(engine: Engine, client: httpx.Client) -> Worker:
    return Worker(engine, BOX, client, PRICING, now=lambda: NOW)


def test_worker_runs_campaign_to_the_end(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1), api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=2), NOW)
    worker = worker_for(campaign_db, client)
    assert worker.work_once() is True
    assert progress(campaign_db, campaign_id).status == "done"
    assert worker.work_once() is True  # puis les fiches sont rapprochées du registre (C44)
    assert worker.work_once() is False


def test_worker_stops_on_signal(campaign_db: Engine) -> None:
    client, _ = fake_client(pages())
    stop = threading.Event()
    thread = threading.Thread(target=worker_for(campaign_db, client).run_forever, args=(stop, 0.01))
    thread.start()
    stop.set()
    thread.join(2)
    assert not thread.is_alive()


def test_C40_two_campaigns_advance_in_turn(campaign_db: Engine) -> None:
    queries: list[str] = []
    serve = pages(*[[api_place(n)] for n in range(10)])

    def handler(request: httpx.Request) -> httpx.Response:
        queries.append(json.loads(request.content)["textQuery"])
        return serve(request)

    client, _ = fake_client(handler)
    create_campaign(campaign_db, request(target=9), NOW)
    create_campaign(campaign_db, request(target=9, trades=("fleuriste",)), NOW)
    seconds = itertools.count()
    worker = Worker(
        campaign_db, BOX, client, PRICING, now=lambda: NOW + timedelta(seconds=next(seconds))
    )
    for _ in range(4):
        worker.work_once()
    assert queries == ["cuisiniste Lyon", "fleuriste Lyon", "cuisiniste Lyon", "fleuriste Lyon"]


def test_C40_page_then_campaign_given_back_for_the_next_worker(campaign_db: Engine) -> None:
    client, recorder = fake_client(pages([api_place(1)], [api_place(2)], [api_place(3)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    assert worker_for(campaign_db, client).work_once() is True
    assert len(recorder.requests) == 1  # un SIGTERM n'attend jamais plus d'une page
    assert progress(campaign_db, campaign_id).found == 1
    assert claim_next(campaign_db, NOW, "suivant") == campaign_id


def test_C40_worker_never_releases_a_campaign_taken_over(campaign_db: Engine) -> None:
    serve = pages([api_place(1)], [api_place(2)], [api_place(3)])

    def handler(request: httpx.Request) -> httpx.Response:
        with campaign_db.begin() as conn:
            conn.execute(text("UPDATE campaigns SET claimed_by = 'autre worker'"))
        return serve(request)

    client, recorder = fake_client(handler)
    create_campaign(campaign_db, request(target=9), NOW)
    assert worker_for(campaign_db, client).work_once() is True
    with campaign_db.connect() as conn:
        owner = conn.execute(text("SELECT claimed_by FROM campaigns")).scalar_one()
    assert (len(recorder.requests), owner) == (1, "autre worker")


def test_C53_idle_worker_checks_mail_servers(campaign_db: Engine) -> None:
    """Rien à chercher, registre à jour : la tâche de fond vérifie les serveurs mail."""
    from tests.application.test_mail_check import with_emails

    with_emails(campaign_db)
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET registry_status = 'sûr'")
        conn.exec_driver_sql("UPDATE campaigns SET status = 'done'")
    asked: list[str] = []

    def lookup(domain: str) -> str:
        asked.append(domain)
        return "mx"

    client, _ = fake_client(pages())
    worker = Worker(campaign_db, BOX, client, PRICING, now=lambda: NOW, mail_lookup=lookup)
    assert worker.work_once() is True and len(asked) == 3
    assert worker.work_once() is False


def test_rule_3_end_to_end_worker_never_asks_the_real_dns() -> None:
    """En bout en bout (faux services), la vérification des serveurs mail est coupée."""
    from prospection.sources.mail_domain import mail_server
    from prospection.worker import mail_lookup_for

    assert mail_lookup_for("http://127.0.0.1:8099") is None
    assert mail_lookup_for(None) is mail_server


def test_C53_idle_mail_check_at_most_every_ten_minutes(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rien à vérifier : la recherche de domaines n'est pas relancée à chaque pause."""
    import prospection.idle_work as worker_module

    calls: list[object] = []
    clock = [NOW]

    def counting(*args: object) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(worker_module, "check_mail_domains", counting)
    client, _ = fake_client(pages())
    worker = Worker(campaign_db, BOX, client, PRICING, now=lambda: clock[0],
                    mail_lookup=lambda d: "mx")  # fmt: skip
    worker.work_once()
    worker.work_once()
    assert len(calls) == 1
    clock[0] = NOW + timedelta(minutes=11)
    worker.work_once()
    assert len(calls) == 2
