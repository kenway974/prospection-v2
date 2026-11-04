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
