"""C149, C150 : entre deux campagnes, la tâche de fond complète les entreprises, sans boucle."""

from datetime import timedelta

import pytest
from sqlalchemy import Engine

from prospection.worker import Worker
from tests.application.campaign_helpers import BOX, NOW, PRICING, pages
from tests.fake_http import fake_client


def test_C149_idle_worker_completes_companies_then_pauses(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    import prospection.idle_work as idle

    results, calls, clock = [1, 0, 0], [], [NOW]

    def details(*args: object) -> int:
        calls.append(args)
        return results.pop(0)

    monkeypatch.setattr(idle, "detail_companies", details)
    worker = Worker(campaign_db, BOX, fake_client(pages())[0], PRICING, now=lambda: clock[0])
    assert worker.work_once() is True  # une entreprise complétée
    worker.work_once()
    worker.work_once()
    assert len(calls) == 2  # rien à faire : pause de 10 minutes
    clock[0] = NOW + timedelta(minutes=11)
    worker.work_once()
    assert len(calls) == 3


def test_C156_idle_worker_runs_requested_audits_with_its_site_reader(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    import prospection.idle_work as idle

    seen: list[object] = []
    monkeypatch.setattr(idle, "detail_companies", lambda *a, **k: 0)

    def run(engine: Engine, sites: object, now: object) -> int:
        seen.append(sites)
        return 1

    monkeypatch.setattr(idle, "run_reaudits", run)
    reader = lambda place, keywords: None  # noqa: E731
    worker = Worker(campaign_db, BOX, fake_client(pages())[0], PRICING, now=lambda: NOW,
                    sites=reader)  # fmt: skip
    assert worker.work_once() is True and seen == [reader]


def test_C163_idle_worker_checks_replies_at_most_every_half_hour(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    import prospection.idle_work as idle
    from prospection.sources.gmail import GmailOAuth

    calls: list[object] = []
    clock = [NOW]
    monkeypatch.setattr(idle, "detail_companies", lambda *a, **k: 0)

    def replies(*args: object) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(idle, "check_replies", replies)
    worker = Worker(campaign_db, BOX, fake_client(pages())[0], PRICING, now=lambda: clock[0],
                    gmail=GmailOAuth("id", "secret"))  # fmt: skip
    worker.work_once()
    worker.work_once()
    assert len(calls) == 1
    clock[0] = NOW + timedelta(minutes=31)
    worker.work_once()
    assert len(calls) == 2


def test_C169_idle_worker_sends_the_mail_queue(campaign_db: Engine) -> None:
    calls: list[int] = []

    def mail_queue() -> bool:
        calls.append(1)
        return len(calls) == 1

    worker = Worker(campaign_db, BOX, fake_client(pages())[0], PRICING, now=lambda: NOW,
                    mail_queue=mail_queue)  # fmt: skip
    assert worker.work_once() is True
    worker.work_once()
    assert len(calls) == 2


def test_C177_idle_worker_sends_the_sms_queue(campaign_db: Engine) -> None:
    calls: list[int] = []

    def sms_queue() -> bool:
        calls.append(1)
        return len(calls) == 1

    worker = Worker(campaign_db, BOX, fake_client(pages())[0], PRICING, now=lambda: NOW,
                    sms_queue=sms_queue)  # fmt: skip
    assert worker.work_once() is True
    worker.work_once()
    assert len(calls) == 2


def test_C182_worker_queues_the_mails_when_a_campaign_ends(
    campaign_db: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    import prospection.worker as worker_module
    from prospection.application.step_flow import StepOutcome

    seen: list[int] = []
    monkeypatch.setattr(worker_module, "claim_next", lambda *a: 7)
    monkeypatch.setattr(worker_module, "run_step", lambda *a: StepOutcome(done=True))
    monkeypatch.setattr(worker_module, "after_campaign", lambda *a: None)
    monkeypatch.setattr(
        worker_module, "queue_campaign_mails", lambda e, b, cid, now: seen.append(cid)
    )
    Worker(campaign_db, BOX, fake_client(pages())[0], PRICING, now=lambda: NOW).work_once()
    assert seen == [7]
