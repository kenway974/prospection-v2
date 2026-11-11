"""C175 : Réglages → SMS : activés, expéditeur « Kenny » par défaut, plafond ; clé Brevo."""

import html

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.storage.sms_settings_store import load_sms_settings
from tests.fake_http import Recorder
from tests.ui.test_mail_screens import web  # noqa: F401 (fixture)
from tests.ui.test_settings_keys import ORIGIN


def test_C175_sms_settings_page(web: tuple[TestClient, Recorder], mail_db: Engine) -> None:  # noqa: F811
    client, _ = web
    assert 'href="/reglages/sms"' in client.get("/reglages").text
    page = html.unescape(client.get("/reglages/sms").text)
    assert 'value="Kenny"' in page and "Brevo" in page and 'href="/reglages/cles"' in page
    client.post("/reglages/sms", data={"actifs": "on", "expediteur": "Kenny", "plafond": "20"},
                headers=ORIGIN)  # fmt: skip
    with mail_db.connect() as conn:
        saved = load_sms_settings(conn)
    assert (saved.enabled, saved.daily_limit) == (True, 20)
    wrong = client.post("/reglages/sms", data={"expediteur": "Kenny Pignolet", "plafond": "20"},
                        headers=ORIGIN)  # fmt: skip
    assert wrong.status_code == 400 and "3 à 11 lettres" in html.unescape(wrong.text)
