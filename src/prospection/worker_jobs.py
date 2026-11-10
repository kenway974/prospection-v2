"""Travaux de la tâche de fond branchés sur les vrais services (point d'entrée seulement) :
lecture des sites (C166, C174), envoi groupé du mail d'audit (C169) et des SMS (C177, C180)."""

import random
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from sqlalchemy import Engine

from prospection.application.mail_queue_run import send_next
from prospection.application.site_check import check_site
from prospection.application.site_verdict import SiteChecker
from prospection.application.sms_queue_run import send_next_sms, sync_stops
from prospection.config import Settings
from prospection.domain.place import Place
from prospection.domain.site_report import SiteReport
from prospection.sources.browser_process import render_isolated
from prospection.sources.web_reader import ReadResult
from prospection.storage.secret_box import SecretBox
from prospection.storage.shared_sites import companies_on_host


def site_checker(settings: Settings, engine: Engine, web: httpx.Client) -> SiteChecker:
    def browser(url: str, seconds: float) -> ReadResult:  # C166 : sites en JavaScript
        return render_isolated(url, seconds, settings.test_services_url)

    def shared(host: str, name: str) -> int:  # C174 : autres entreprises sur ce domaine
        with engine.connect() as conn:
            return companies_on_host(conn, host, name)

    def sites(place: Place, keywords: tuple[str, ...]) -> SiteReport:
        return check_site(web, place, keywords, datetime.now(UTC).year, browser, shared)

    return sites


def mail_queue_job(
    settings: Settings, engine: Engine, box: SecretBox, client: httpx.Client
) -> Callable[[], bool]:
    rng = random.SystemRandom()  # attente entre deux envois, tirée au hasard

    def mail_queue() -> bool:  # C169 : envoi groupé, au rythme de send_pace
        return send_next(engine, box, client, settings.gmail_oauth(), settings.public_base(),
                         datetime.now(UTC), settings.timezone, rng)  # fmt: skip

    return mail_queue


def sms_job(
    settings: Settings, engine: Engine, box: SecretBox, client: httpx.Client
) -> Callable[[], bool]:
    def sms_queue() -> bool:  # STOP de Brevo une fois par jour, puis le prochain SMS
        now = datetime.now(UTC)
        synced = sync_stops(engine, box, client, now)
        return synced or send_next_sms(engine, box, client, settings.gmail_oauth(), now,
                                       settings.timezone)  # fmt: skip

    return sms_queue
