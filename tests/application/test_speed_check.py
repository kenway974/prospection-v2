"""Vitesse mobile mesurée par la tâche de fond : une fois par site, dans le calme."""

import json
import threading

import httpx
import pytest
from sqlalchemy import Engine

from prospection.application.prospect_card import card
from prospection.application.speed_check import SpeedPaused, check_next_site, speed_job
from prospection.domain.site_audit import Audit
from prospection.domain.site_report import SiteReport
from prospection.storage.alerts import unseen_alerts
from prospection.storage.site_codec import encode_site
from tests.application.campaign_helpers import BOX, NOW
from tests.application.test_call_tracking import PARIS, add
from tests.fake_http import fake_client, json_reply
from tests.sources.test_page_speed import ANSWER
from tests.storage.test_campaigns import PLACE

AUDIT = Audit(85, (), "WordPress", https=True, mobile=True, contact_form=True)


def with_site(engine: Engine) -> int:
    add(engine, PLACE)
    report = encode_site(SiteReport("fiche Google", url="https://atelier.fr", audit=AUDIT))
    with engine.begin() as conn:
        pid = int(conn.exec_driver_sql("SELECT max(id) FROM prospects").scalar_one())
        conn.exec_driver_sql("UPDATE prospects SET site_json = %(s)s::jsonb WHERE id = %(id)s",
                             {"s": json.dumps(report), "id": pid})  # fmt: skip
    return pid


def test_each_site_measured_once_and_shown(campaign_db: Engine) -> None:
    pid = with_site(campaign_db)
    client, seen = fake_client(json_reply(200, ANSWER))
    assert check_next_site(campaign_db, BOX, client, NOW)
    assert not check_next_site(campaign_db, BOX, client, NOW)  # déjà mesuré
    assert len(seen.requests) == 1
    shown = card(campaign_db, pid, NOW, PARIS).prospect.site
    assert shown is not None and shown.speed is not None and shown.speed.score == 34
    assert shown.audit == AUDIT  # le reste du rapport est gardé


def test_busy_google_retried_later_refused_api_alerted(campaign_db: Engine) -> None:
    with_site(campaign_db)
    with pytest.raises(SpeedPaused):
        check_next_site(campaign_db, BOX, fake_client(json_reply(503, {}))[0], NOW)
    with pytest.raises(SpeedPaused):
        check_next_site(campaign_db, BOX, fake_client(json_reply(403, {}))[0], NOW)
    with campaign_db.connect() as conn:
        [alert] = unseen_alerts(conn)
    assert "PageSpeed Insights API" in alert.message
    assert check_next_site(campaign_db, BOX, fake_client(json_reply(200, ANSWER))[0], NOW)


def test_nothing_without_site_or_key(campaign_db: Engine) -> None:
    add(campaign_db, PLACE)  # pas de site adopté
    client, seen = fake_client(json_reply(200, ANSWER))
    assert not check_next_site(campaign_db, BOX, client, NOW) and seen.requests == []
    with_site(campaign_db)
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")
    assert not check_next_site(campaign_db, BOX, client, NOW) and seen.requests == []


def test_job_runs_aside_one_pass_at_a_time(campaign_db: Engine) -> None:
    with_site(campaign_db)
    started, release = threading.Event(), threading.Event()

    def slow(request: httpx.Request) -> httpx.Response:
        started.set()
        release.wait(5)
        return httpx.Response(200, json=ANSWER)

    job = speed_job(campaign_db, BOX, fake_client(slow)[0])
    assert job(NOW) is True and started.wait(5)
    assert job(NOW) is False  # passage déjà en cours
    release.set()
