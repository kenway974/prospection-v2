"""C144 : écran Réglages → Mail d'audit et connexion Gmail (faux Google)."""

import html
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.ui.app import create_app
from prospection.ui.deps import get_http_client, get_now
from prospection.ui.routes_mail_settings import STATE_COOKIE
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.application.test_mail_settings import clean  # noqa: F401 (remise à zéro)
from tests.fake_http import fake_client, json_reply
from tests.sources.test_gmail import id_token
from tests.ui.test_settings_keys import NOW, ORIGIN

GOOGLE = {"refresh_token": "jeton-long", "id_token": id_token("kapignolet18@gmail.com")}


def make_client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    app = create_app(settings, engine)
    app.dependency_overrides[get_now] = lambda: NOW
    app.dependency_overrides[get_http_client] = lambda: fake_client(json_reply(200, GOOGLE))[0]
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(settings, NOW))
        yield test_client


@pytest.fixture
def mail_client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    configured = settings.model_copy(update={
        "gmail_client_id": "id", "gmail_client_secret": SecretStr("secret"),
        "public_url": "https://testserver"})  # fmt: skip
    yield from make_client(configured, engine)


@pytest.fixture
def bare_client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    yield from make_client(settings, engine)


def test_C144_settings_form_saved(mail_client: TestClient) -> None:
    assert "Mail d'audit" in html.unescape(mail_client.get("/reglages").text)
    response = mail_client.post("/reglages/mail", headers=ORIGIN, follow_redirects=False, data={
        "nom": "Kenny Pignolet", "telephone": "06 12 34 56 78", "portfolio": "https://kenny.dev",
        "calendly": "", "jours": "2"})  # fmt: skip
    assert response.status_code == 303
    page = html.unescape(mail_client.get("/reglages/mail").text)
    assert 'value="Kenny Pignolet"' in page and 'value="https://kenny.dev"' in page


def test_C144_bad_settings_said_next_to_the_field(mail_client: TestClient) -> None:
    data = {"nom": "Kenny", "telephone": "", "portfolio": "kenny.dev", "calendly": "", "jours": "2"}
    response = mail_client.post("/reglages/mail", headers=ORIGIN, data=data)
    assert response.status_code == 400
    assert "adresse complète du portfolio" in html.unescape(response.text)


def test_C144_gmail_connected_through_google(mail_client: TestClient) -> None:
    start = mail_client.get("/reglages/gmail/connecter", follow_redirects=False)
    assert start.status_code == 303
    assert start.headers["location"].startswith("https://accounts.google.com/")
    state = mail_client.cookies.get(STATE_COOKIE)
    assert state and f"state={state}" in start.headers["location"]
    back = mail_client.get(f"/reglages/gmail/retour?code=c&state={state}", follow_redirects=False)
    assert back.status_code == 303
    page = html.unescape(mail_client.get("/reglages/mail").text)
    assert "kapignolet18@gmail.com" in page and "jeton-long" not in page


def test_C144_forged_return_is_refused(mail_client: TestClient) -> None:
    mail_client.get("/reglages/gmail/connecter", follow_redirects=False)
    response = mail_client.get("/reglages/gmail/retour?code=c&state=faux")
    assert response.status_code == 400 and "Recommencez" in html.unescape(response.text)
    assert "kapignolet18@gmail.com" not in html.unescape(mail_client.get("/reglages/mail").text)


def test_C144_refused_consent_said_plainly(mail_client: TestClient) -> None:
    mail_client.get("/reglages/gmail/connecter", follow_redirects=False)
    state = mail_client.cookies.get(STATE_COOKIE)
    response = mail_client.get(f"/reglages/gmail/retour?error=access_denied&state={state}")
    assert response.status_code == 400 and "pas été donné" in html.unescape(response.text)


def test_C144_without_google_identifiers_says_what_to_do(bare_client: TestClient) -> None:
    page = html.unescape(bare_client.get("/reglages/mail").text)
    assert "GMAIL_CLIENT_ID" in page and "/reglages/gmail/connecter" not in page


def test_C144_disconnect_says_when_google_did_not_confirm(
    settings: Settings, engine: Engine
) -> None:
    from tests.fake_http import timeout

    configured = settings.model_copy(update={
        "gmail_client_id": "id", "gmail_client_secret": SecretStr("secret"),
        "public_url": "https://testserver"})  # fmt: skip
    for client in make_client(configured, engine):
        client.app.dependency_overrides[get_http_client] = (  # type: ignore[attr-defined]
            lambda: fake_client(json_reply(200, GOOGLE))[0]
        )
        client.get("/reglages/gmail/connecter", follow_redirects=False)
        state = client.cookies.get(STATE_COOKIE)
        client.get(f"/reglages/gmail/retour?code=c&state={state}", follow_redirects=False)
        client.app.dependency_overrides[get_http_client] = lambda: fake_client(timeout)[0]  # type: ignore[attr-defined]
        page = html.unescape(client.post("/reglages/gmail/deconnecter", headers=ORIGIN).text)
        assert "myaccount.google.com/permissions" in page and "kapignolet18" not in page


def test_C163_settings_ask_to_reconnect_gmail_for_replies(
    mail_client: TestClient, engine: Engine
) -> None:
    from prospection.storage.mail_settings import block_replies, save_gmail
    from tests.application.campaign_helpers import BOX

    with engine.begin() as conn:
        save_gmail(conn, "kapignolet18@gmail.com", BOX.encrypt("jeton"), NOW)
        block_replies(conn)
    page = html.unescape(mail_client.get("/reglages/mail").text)
    assert "repérer les réponses" in page and "Délier Gmail" in page
