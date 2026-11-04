"""C144 : réglages du mail et compte Gmail relié (jeton chiffré, jamais affiché)."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from prospection.application.mail_settings import (
    REDIRECT_PATH,
    change_mail_settings,
    connected_address,
    disconnect_gmail,
    finish_gmail,
    gmail_refresh_token,
    load_settings_screen,
)
from prospection.domain.mail_settings import InvalidMailSettings, MailSettings
from prospection.sources.gmail import GmailOAuth
from tests.application.campaign_helpers import BOX, NOW
from tests.fake_http import fake_client, json_reply
from tests.sources.test_gmail import id_token

OAUTH = GmailOAuth("id", "secret")
BASE = "https://app.fr"


@pytest.fixture(autouse=True)
def clean(engine: Engine) -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "UPDATE mail_settings SET sender_name = NULL, phone = NULL, portfolio = NULL, "
            "calendly = NULL, reminder_days = 2, gmail_address = NULL, gmail_token = NULL, "
            "gmail_connected_at = NULL"
        )


def test_C144_settings_saved_and_reloaded(engine: Engine) -> None:
    assert load_settings_screen(engine) == MailSettings(None, None, None, None, 2)
    change_mail_settings(engine, "Kenny", "", "https://kenny.dev", "", "1")
    assert load_settings_screen(engine) == MailSettings("Kenny", None, "https://kenny.dev", None, 1)
    with pytest.raises(InvalidMailSettings):
        change_mail_settings(engine, "", "", "", "", "9")
    assert load_settings_screen(engine).sender_name == "Kenny"  # rien changé


def test_C144_gmail_connected_with_encrypted_token_then_disconnected(engine: Engine) -> None:
    reply = {"refresh_token": "jeton-long", "id_token": id_token("kapignolet18@gmail.com")}
    client, recorder = fake_client(json_reply(200, reply))
    assert finish_gmail(engine, BOX, client, OAUTH, BASE, "code", NOW) == "kapignolet18@gmail.com"
    assert f"redirect_uri={BASE}{REDIRECT_PATH}".replace(":", "%3A").replace("/", "%2F") in (
        recorder.requests[0].content.decode()
    )
    assert connected_address(engine) == "kapignolet18@gmail.com"
    assert gmail_refresh_token(engine, BOX) == "jeton-long"
    with engine.connect() as conn:
        stored = conn.exec_driver_sql("SELECT gmail_token FROM mail_settings").scalar()
    assert stored is not None and b"jeton-long" not in bytes(stored)
    disconnect_gmail(engine)
    assert connected_address(engine) is None and gmail_refresh_token(engine, BOX) is None
