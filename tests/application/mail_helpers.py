"""Prospect audité, réglages du mail et faux Google pour les tests du mail d'audit."""

import dataclasses
import json
from collections.abc import Iterator

import httpx
import pytest
from sqlalchemy import Engine

from prospection.application.mail_settings import change_mail_settings
from prospection.domain.criteria import Verdict
from prospection.domain.site_audit import Audit
from prospection.domain.site_contacts import Contacts
from prospection.domain.site_report import SiteReport
from prospection.sources.gmail import GmailOAuth
from prospection.storage.campaigns import create_campaign
from prospection.storage.mail_settings import save_gmail
from prospection.storage.prospects import insert_prospect
from tests.application.campaign_helpers import BOX, NOW, request
from tests.fake_http import Recorder, fake_client
from tests.storage.test_campaigns import PLACE, STEPS

OAUTH = GmailOAuth("id", "secret")
BASE = "https://app.fr"
AUDIT = Audit(40, ("Pas de HTTPS", "Pas adapté au mobile", "Aucun lien vers les réseaux sociaux"),
              "WordPress", False, False, True, "en haut de l'accueil",
              ("no_https", "no_mobile", "no_social"))  # fmt: skip
CONTACTS = Contacts(("contact@martin.fr", "noreply@martin.fr"), (), ())
SITE = SiteReport("fiche Google", "http://martin.fr/", audit=AUDIT, contacts=CONTACTS)


def add_audited(
    engine: Engine, site: SiteReport | None = SITE, contacts_email: str | None = None
) -> int:
    """`contacts_email` : une autre adresse que celle du site d'exemple (une adresse ne reçoit
    qu'un mail d'audit)."""
    if site is not None and contacts_email:
        site = dataclasses.replace(site, contacts=Contacts((contacts_email,), (), ()))
    with engine.begin() as conn:
        campaign_id = create_campaign(conn, request(), STEPS, NOW)
        insert_prospect(conn, campaign_id, PLACE, "plombier", Verdict(True, (), ()), NOW, site)
        pid = int(conn.exec_driver_sql("SELECT max(id) FROM prospects").scalar_one())
        conn.exec_driver_sql("UPDATE prospects SET registry_status = 'sûr' WHERE id = %(p)s",
                             {"p": pid})  # fmt: skip
        return pid


def ready(engine: Engine) -> None:
    """Réglages faits et Gmail relié."""
    change_mail_settings(engine, "Kenny Pignolet", "", "https://kenny.dev", "", "2")
    with engine.begin() as conn:
        save_gmail(conn, "kapignolet18@gmail.com", BOX.encrypt("jeton-long"), NOW)


def google(send_status: int = 200) -> tuple[httpx.Client, Recorder]:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "court"})
        return httpx.Response(send_status, json={"id": "m1", "threadId": "fil-1"})

    return fake_client(handler)


def sent_raw(recorder: Recorder) -> str:
    import base64

    raw = json.loads(recorder.requests[-1].content)["raw"]
    return base64.urlsafe_b64decode(raw + "==").decode()


@pytest.fixture
def mail_db(campaign_db: Engine) -> Iterator[Engine]:
    yield campaign_db
    with campaign_db.begin() as conn:
        conn.exec_driver_sql(
            "DELETE FROM mail_optouts; DELETE FROM mail_sends; UPDATE mail_settings SET "
            "sender_name = NULL, phone = NULL, portfolio = NULL, calendly = NULL, "
            "reminder_days = 2, gmail_address = NULL, gmail_token = NULL, "
            "gmail_connected_at = NULL, replies_blocked = false, daily_limit = 30, "
            "queue_paused = NULL; DELETE FROM sms_optouts; DELETE FROM sms_sends; "
            "UPDATE sms_settings SET enabled = false, sender = 'Kenny', daily_limit = 30, "
            "optouts_synced_at = NULL"
        )
