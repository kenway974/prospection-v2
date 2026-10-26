"""Tâche de fond : fait avancer les campagnes (`python -m prospection.worker`).

Deuxième service Railway, même image. S'arrête proprement sur SIGTERM. Les
journaux ne contiennent ni clé ni adresse complète.
"""

import logging
import signal
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from sqlalchemy import Engine

from prospection.application.campaign_queue import claim_next, release_until
from prospection.application.campaign_step import run_step
from prospection.domain.google_cost import Pricing, load_pricing
from prospection.storage.secret_box import SecretBox

logger = logging.getLogger("prospection.worker")


class Worker:
    def __init__(
        self, engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:  # fmt: skip
        self.engine, self.box, self.client, self.pricing = engine, box, client, pricing
        self.now = now
        self.worker_id = uuid.uuid4().hex

    def work_once(self) -> bool:
        """Lit une page de la campagne la plus en attente, puis la rend à la file.

        Vrai si travail. Les campagnes avancent ainsi à tour de rôle, et un arrêt
        (SIGTERM d'un déploiement) n'attend jamais plus d'une page.
        """
        campaign_id = claim_next(self.engine, self.now(), self.worker_id)
        if campaign_id is None:
            return False
        outcome = run_step(
            self.engine, self.box, self.client, self.pricing, campaign_id, self.now()
        )
        if outcome.done:
            logger.info("Campagne %s terminée", campaign_id)
        else:
            release_until(self.engine, campaign_id, outcome.retry_at or self.now(), self.worker_id)
        return True

    def run_forever(self, stop: threading.Event, idle_seconds: float = 2.0) -> None:
        while not stop.is_set():
            try:
                worked = self.work_once()
            except Exception:  # une campagne en échec ne doit pas arrêter le worker
                logger.exception("Erreur pendant une campagne")
                worked = False
            if not worked:
                stop.wait(idle_seconds)


def main() -> None:  # pragma: no cover (point d'entrée, testé en bout en bout)
    from prospection.config import load_settings
    from prospection.http_client import make_client
    from prospection.storage.db import make_engine

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # pas d'adresses d'appels au journal
    settings = load_settings()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    box = SecretBox(settings.encryption_key.get_secret_value())
    with make_client(settings.google_places_test_url) as client:
        worker = Worker(make_engine(settings.database_url), box, client, load_pricing())
        logger.info("Tâche de fond démarrée")
        worker.run_forever(stop)


if __name__ == "__main__":  # pragma: no cover
    main()
