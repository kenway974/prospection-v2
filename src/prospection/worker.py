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

from prospection.application.backup import backup_job
from prospection.application.campaign_end import after_campaign
from prospection.application.campaign_queue import claim_next, release_until
from prospection.application.campaign_step import run_step
from prospection.application.periodic import regular_jobs
from prospection.application.push import push_job
from prospection.application.schedules import run_due_schedule
from prospection.application.site_verdict import SiteChecker, skip_sites
from prospection.application.speed_check import SpeedJob
from prospection.domain.google_cost import Pricing, load_pricing
from prospection.idle_work import IdleWork
from prospection.sources.gmail import GmailOAuth
from prospection.sources.mail_domain import mail_server
from prospection.storage.secret_box import SecretBox

logger = logging.getLogger("prospection.worker")


class Worker:
    def __init__(
        self, engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        sites: SiteChecker = skip_sites,
        mail_lookup: Callable[[str], str | None] | None = None, timezone: str = "Europe/Paris",
        backup: Callable[[datetime], object] | None = None,
        push: Callable[[datetime], object] | None = None, speed: SpeedJob | None = None,
        gmail: GmailOAuth | None = None,
    ) -> None:  # fmt: skip
        self.engine, self.box, self.client, self.pricing = engine, box, client, pricing
        self.now, self.sites, self.mail_lookup = now, sites, mail_lookup
        self.timezone = timezone
        self.idle = IdleWork(engine, box, client, pricing, now, mail_lookup, sites, gmail)
        self.reminders, self.periodic = regular_jobs(
            engine, box, client, pricing, timezone, backup, now(), push, speed
        )
        self.speed = speed
        self.worker_id = uuid.uuid4().hex

    def work_once(self) -> bool:
        """Lit une page de la campagne la plus en attente, puis la rend à la file.

        Vrai si travail. Les campagnes avancent ainsi à tour de rôle, et un arrêt
        (SIGTERM d'un déploiement) n'attend jamais plus d'une page.
        """
        for job in (self.reminders, *self.periodic):  # même en pleine campagne
            job.maybe_run(self.now())
        if run_due_schedule(self.engine, self.now(), self.timezone):  # C77
            return True
        campaign_id = claim_next(self.engine, self.now(), self.worker_id)
        if campaign_id is None:
            return self._between_campaigns()
        outcome = run_step(
            self.engine, self.box, self.client, self.pricing, campaign_id, self.now(), self.sites
        )
        if outcome.done:
            logger.info("Campagne %s terminée", campaign_id)
            after_campaign(self.engine, campaign_id, self.now())  # C78, C98
        else:
            release_until(self.engine, campaign_id, outcome.retry_at or self.now(), self.worker_id)
        return True

    def _between_campaigns(self) -> bool:
        """Rien à chercher : envois CRM, registre, compléments, mises à jour, serveurs mail."""
        return self.idle.run()

    def run_forever(self, stop: threading.Event, idle_seconds: float = 2.0) -> None:
        while not stop.is_set():
            try:
                worked = self.work_once()
            except Exception:  # une campagne en échec ne doit pas arrêter le worker
                logger.exception("Erreur pendant une campagne")
                worked = False
            if not worked:
                stop.wait(idle_seconds)


def mail_lookup_for(test_services_url: str | None) -> Callable[[str], str | None] | None:
    """Vrai DNS en production ; aucun en bout en bout (faux services, règle 3)."""
    return None if test_services_url else mail_server


def main() -> None:  # pragma: no cover (point d'entrée, testé en bout en bout)
    from prospection.application.site_check import check_site
    from prospection.config import load_settings
    from prospection.domain.place import Place
    from prospection.domain.site_report import SiteReport
    from prospection.http_client import make_client
    from prospection.monitoring import start_monitoring
    from prospection.sources.browser_process import render_isolated
    from prospection.sources.safe_network import make_web_client
    from prospection.sources.web_reader import ReadResult
    from prospection.storage.db import make_engine

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # pas d'adresses d'appels au journal
    settings = load_settings()
    dsn = settings.sentry_dsn.get_secret_value() if settings.sentry_dsn else None
    start_monitoring(dsn, "worker")
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    box = SecretBox(settings.encryption_key.get_secret_value())
    web = make_web_client(settings.test_services_url)  # sites des prospects : garde SSRF

    def browser(url: str, seconds: float) -> ReadResult:  # C166 : sites en JavaScript
        return render_isolated(url, seconds, settings.test_services_url)

    def sites(place: Place, keywords: tuple[str, ...]) -> SiteReport:
        return check_site(web, place, keywords, datetime.now(UTC).year, browser)

    with make_client(settings.test_services_url) as client, web:
        engine = make_engine(settings.database_url)
        lookup = mail_lookup_for(settings.test_services_url)
        key = settings.encryption_key.get_secret_value()
        backup = backup_job(settings.backup_target(), key, settings.database_url, engine, client)
        push = push_job(settings.vapid_keys(), engine, client, settings.timezone)
        worker = Worker(engine, box, client, load_pricing(), sites=sites, mail_lookup=lookup,
                        timezone=settings.timezone, backup=backup, push=push,
                        speed=SpeedJob(engine, box, client),
                        gmail=settings.gmail_oauth())  # fmt: skip
        logger.info("Tâche de fond démarrée")
        worker.run_forever(stop)
        if worker.speed:  # arrêt propre : la mesure en cours finit avant la fermeture
            worker.speed.join(timeout=15)


if __name__ == "__main__":  # pragma: no cover
    main()
