"""Travaux réguliers de la tâche de fond (purge, vérification des API, sauvegarde) : chacun
à son rythme ; une erreur sur l'un n'empêche pas les autres."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.api_watch import weekly_api_check
from prospection.application.crm_index import refresh_crm_index
from prospection.application.privacy import purge
from prospection.application.reminders import remind_due_actions
from prospection.domain.google_cost import Pricing
from prospection.storage.secret_box import SecretBox

logger = logging.getLogger(__name__)


@dataclass
class Periodic:
    name: str
    every: timedelta
    run: Callable[[datetime], object]
    next_at: datetime = field(default_factory=lambda: datetime.min.replace(tzinfo=UTC))

    def maybe_run(self, now: datetime) -> None:
        if now < self.next_at:
            return
        self.next_at = now + self.every
        try:
            self.run(now)
        except Exception:
            logger.exception("Travail régulier « %s » en échec", self.name)


def regular_jobs(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, timezone: str,
    backup: Callable[[datetime], object] | None, start: datetime,
    push: Callable[[datetime], object] | None = None,
) -> tuple[Periodic, list[Periodic]]:  # fmt: skip
    """Rappels (chaque minute) et travaux réguliers ; tous tournent même en pleine campagne.
    Purge, vérification et sauvegarde attendent 5 min après le démarrage (pas de rafale à
    chaque déploiement)."""
    later = start + timedelta(minutes=5)
    reminders = Periodic(
        "rappels", timedelta(minutes=1), lambda now: remind_due_actions(engine, now, timezone)
    )  # C108
    jobs = [
        Periodic("index du CRM", timedelta(hours=1),
                 lambda now: refresh_crm_index(engine, box, client, now)),  # C32
        Periodic("purge RGPD", timedelta(hours=6), lambda now: purge(engine, now), later),  # C94
        Periodic("vérification des API", timedelta(hours=1),
                 lambda now: weekly_api_check(engine, box, client, pricing, now), later),  # C99
        *([Periodic("sauvegarde", timedelta(hours=1), backup, later)] if backup else []),  # C91
        *([Periodic("notifications", timedelta(seconds=20), push)] if push else []),
    ]  # fmt: skip
    return reminders, jobs
