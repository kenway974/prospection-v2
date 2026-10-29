"""Vitesse mobile des sites des prospects retenus (PageSpeed Insights), par la tâche de fond,
dans un fil à part : une analyse dure souvent 10 à 40 s, les rappels n'attendent pas."""

import logging
import threading
from collections.abc import Callable
from dataclasses import asdict
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
PAUSE = timedelta(minutes=10)  # Google indisponible ou API refusée : on attend


class SpeedPaused(Exception):
    """Google indisponible ou API refusée : rien de plus pour l'instant."""


def check_next_site(engine: Engine, box: SecretBox, client: httpx.Client, now: datetime) -> bool:
    """Mesure un site en attente ; vrai s'il y en avait un. Lève SpeedPaused si Google ne
    répond pas ou refuse (le site repart dans la file)."""
    key = read_key(engine, box, Service.GOOGLE)
    if key is None:
        return False
    with engine.begin() as conn:
        taken = queue.take_site(conn, now)
    if taken is None:
        return False
    prospect_id, url = taken
    try:
        speed = page_speed(client, key, url)
    except (SpeedBusy, SpeedRefused) as error:
        with engine.begin() as conn:
            queue.give_back(conn, prospect_id)
            if isinstance(error, SpeedRefused):
                add_alert(conn, f"pagespeed:{now:%Y-%m-%d}", "api", str(error),
                          "/reglages/cles", now)  # fmt: skip
        raise SpeedPaused from None
    if speed is not None:  # sinon Google n'a pas pu charger le site : rien de plus
        with engine.begin() as conn:
            queue.save_speed(conn, prospect_id, asdict(speed))
    return True


def speed_job(engine: Engine, box: SecretBox, client: httpx.Client) -> Callable[[datetime], object]:
    """Travail régulier : quelques sites à chaque passage, jamais deux passages à la fois."""
    running, state = threading.Lock(), {"until": datetime.min.replace(tzinfo=UTC)}

    def work(now: datetime) -> None:
        try:
            for _ in range(PER_RUN):
                if not check_next_site(engine, box, client, now):
                    break
        except SpeedPaused:
            state["until"] = now + PAUSE
        except Exception:
            logger.exception("Mesure de vitesse en échec")
        finally:
            running.release()

    def run(now: datetime) -> bool:
        if now < state["until"] or not running.acquire(blocking=False):
            return False
        threading.Thread(target=work, args=(now,), name="vitesse", daemon=True).start()
        return True

    return run
