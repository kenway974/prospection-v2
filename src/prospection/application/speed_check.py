"""Vitesse mobile des sites des prospects retenus (PageSpeed Insights), par la tâche de fond,
dans un fil à part : une analyse dure souvent 10 à 40 s, les rappels n'attendent pas."""

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.domain.services import Service
from prospection.sources.page_speed import SpeedBusy, SpeedRefused, page_speed
from prospection.storage import page_speed_queue as queue
from prospection.storage.alerts import add_alert
from prospection.storage.secret_box import SecretBox

logger = logging.getLogger(__name__)
PER_RUN = 10  # sites mesurés à chaque passage, au plus
BUSY_PAUSE = timedelta(minutes=10)  # Google indisponible : on attend
REFUSED_PAUSE = timedelta(hours=24)  # API non activée sur la clé : une alerte par jour


class SpeedPaused(Exception):
    """Google indisponible ou API refusée : rien de plus pour l'instant."""

    def __init__(self, pause: timedelta) -> None:
        super().__init__("pause")
        self.pause = pause


def check_next_site(engine: Engine, box: SecretBox, client: httpx.Client, now: datetime) -> bool:
    """Mesure un site en attente ; vrai s'il y en avait un. Lève SpeedPaused si Google ne
    répond pas ou refuse : le site est repris plus tard (3 essais au plus)."""
    key = read_key(engine, box, Service.GOOGLE)
    if key is None:
        return False
    with engine.begin() as conn:
        taken = queue.take_site(conn, now)
        known = queue.known_speed(conn, taken[1], now) if taken else None
    if taken is None:
        return False
    prospect_id, url = taken
    if known is not None:  # même site déjà mesuré : rien de plus à demander à Google
        with engine.begin() as conn:
            queue.save_speed(conn, prospect_id, known)
        return True
    try:
        speed = page_speed(client, key, url)
    except SpeedBusy:
        raise SpeedPaused(BUSY_PAUSE) from None
    except SpeedRefused as refused:
        with engine.begin() as conn:
            queue.not_its_fault(conn, prospect_id)
            add_alert(conn, f"pagespeed:{now:%Y-%m-%d}", "api", str(refused),
                      "/reglages/cles", now)  # fmt: skip
        raise SpeedPaused(REFUSED_PAUSE) from None
    if speed is not None:  # sinon Google n'a pas pu charger le site : rien d'inventé
        with engine.begin() as conn:
            queue.save_speed(conn, prospect_id, asdict(speed))
    return True


@dataclass
class SpeedJob:
    """Travail régulier : quelques sites à chaque passage, dans un fil à part (une analyse
    dure 10 à 40 s), jamais deux passages à la fois ; `join` attend le passage en cours."""

    engine: Engine
    box: SecretBox
    client: httpx.Client
    until: datetime = field(default_factory=lambda: datetime.min.replace(tzinfo=UTC))
    thread: threading.Thread | None = None

    def __call__(self, now: datetime) -> bool:
        if now < self.until or (self.thread is not None and self.thread.is_alive()):
            return False
        self.thread = threading.Thread(target=self._work, args=(now,), name="vitesse")
        self.thread.start()
        return True

    def _work(self, now: datetime) -> None:
        try:
            for _ in range(PER_RUN):
                if not check_next_site(self.engine, self.box, self.client, now):
                    break
        except SpeedPaused as paused:
            self.until = now + paused.pause
        except Exception:  # repris plus tard (délai de reprise de la file)
            logger.exception("Mesure de vitesse en échec")

    def join(self, timeout: float | None = None) -> None:
        if self.thread is not None:
            self.thread.join(timeout)
