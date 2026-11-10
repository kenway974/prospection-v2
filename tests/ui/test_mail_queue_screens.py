"""C169, C170 : plafond réglable, page « Envois » : file, annulation, reprise après arrêt."""

import html

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.application.mail_batch import queue_batch
from prospection.storage.mail_queue import pending_ids
from prospection.storage.mail_queue_settings import daily_limit, set_paused
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import add_audited, ready
from tests.fake_http import Recorder
from tests.ui.test_mail_screens import web  # noqa: F401 (fixture)
from tests.ui.test_settings_keys import ORIGIN

Web = tuple[TestClient, Recorder]


def test_C169_daily_limit_set_in_mail_settings(web: Web, mail_db: Engine) -> None:  # noqa: F811
    client, _ = web
    assert 'name="plafond"' in client.get("/reglages/mail").text
    client.post("/reglages/mail/plafond", data={"plafond": "12"}, headers=ORIGIN)
    with mail_db.connect() as conn:
        assert daily_limit(conn) == 12
    wrong = client.post("/reglages/mail/plafond", data={"plafond": "0"}, headers=ORIGIN)
    assert wrong.status_code == 400 and "entre 1 et 200" in html.unescape(wrong.text)


def test_C170_queue_page_cancel_and_resume(web: Web, mail_db: Engine) -> None:  # noqa: F811
    client, _ = web
    ready(mail_db)
    pid = add_audited(mail_db, contacts_email="a@martin.fr")
    queue_batch(mail_db, BOX, [pid], NOW)
    assert 'href="/prospects/envois"' in client.get("/prospects").text
    page = html.unescape(client.get("/prospects/envois").text)
    assert "En attente" in page and "Annuler" in page
    with mail_db.connect() as conn:
        queue_id = conn.exec_driver_sql("SELECT id FROM mail_queue").scalar_one()
    client.post(f"/prospects/envois/{queue_id}/annuler", headers=ORIGIN)
    with mail_db.connect() as conn:
        assert pending_ids(conn) == []
    with mail_db.begin() as conn:
        set_paused(conn, "File arrêtée après 3 refus de Gmail de suite (test).")
    page = html.unescape(client.get("/prospects/envois").text)
    assert "File arrêtée" in page and "Reprendre" in page
    client.post("/prospects/envois/reprendre", headers=ORIGIN)
    assert "File arrêtée" not in html.unescape(client.get("/prospects/envois").text)


def test_C177_queue_page_shows_the_sms_too(web: Web, mail_db: Engine) -> None:  # noqa: F811
    from tests.application.test_sms_batch import sms_ready

    client, _ = web
    sms_ready(mail_db)
    pid = add_audited(mail_db, contacts_email="a@martin.fr")
    queue_batch(mail_db, BOX, [pid], NOW)
    page = html.unescape(client.get("/prospects/envois").text)
    assert "SMS" in page and "après le mail" in page
