"""C145 à C147 : bouton « Mail d'audit » sur la fiche, relecture, envoi (faux Google)."""

import html
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.ui.app import create_app
from prospection.ui.deps import get_http_client, get_now
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import add_audited, google, ready, sent_raw
from tests.fake_http import Recorder
from tests.ui.test_settings_keys import ORIGIN


@pytest.fixture
def web(settings: Settings, mail_db: Engine) -> Iterator[tuple[TestClient, Recorder]]:
    configured = settings.model_copy(update={
        "gmail_client_id": "id", "gmail_client_secret": SecretStr("secret"),
        "public_url": "https://testserver"})  # fmt: skip
    app = create_app(configured, mail_db)
    app.state.box = BOX
    fake, recorder = google()
    app.dependency_overrides[get_now] = lambda: NOW
    app.dependency_overrides[get_http_client] = lambda: fake
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set(COOKIE_NAME, make_session_value(configured, NOW))
        yield client, recorder


def test_C145_button_opens_an_editable_draft(
    web: tuple[TestClient, Recorder], mail_db: Engine
) -> None:
    client, _ = web
    pid = add_audited(mail_db)
    ready(mail_db)
    assert f'href="/prospects/{pid}/mail"' in client.get(f"/prospects/{pid}").text
    page = html.unescape(client.get(f"/prospects/{pid}/mail").text)
    assert "<textarea" in page and 'name="objet"' in page and "contact@martin.fr" in page
    assert "Un clic suffit" in page and "Envoyer" in page


def test_C146_C147_sent_then_card_says_so(
    web: tuple[TestClient, Recorder], mail_db: Engine
) -> None:
    client, recorder = web
    pid = add_audited(mail_db)
    ready(mail_db)
    data = {"a": "contact@martin.fr", "objet": "Votre site", "texte": "Bonjour <b>vous</b>"}
    response = client.post(f"/prospects/{pid}/mail", data=data, headers=ORIGIN,
                           follow_redirects=False)  # fmt: skip
    assert response.status_code == 303 and response.headers["location"] == f"/prospects/{pid}"
    assert "Bonjour <b>vous</b>" in sent_raw(recorder)  # texte simple, envoyé tel quel
    card = html.unescape(client.get(f"/prospects/{pid}").text)
    assert "Mail d'audit envoyé le" in card and f'href="/prospects/{pid}/mail"' not in card


def test_C146_refusal_keeps_the_typed_text(
    web: tuple[TestClient, Recorder], mail_db: Engine
) -> None:
    client, _ = web
    pid = add_audited(mail_db)
    ready(mail_db)
    data = {"a": "contact@martin.fr", "objet": "", "texte": "Mon texte à moi"}
    response = client.post(f"/prospects/{pid}/mail", data=data, headers=ORIGIN)
    page = html.unescape(response.text)
    assert response.status_code == 400 and "Écrivez un objet." in page
    assert "Mon texte à moi" in page


def test_C145_blocked_screen_says_what_to_do(
    web: tuple[TestClient, Recorder], mail_db: Engine
) -> None:
    client, _ = web
    pid = add_audited(mail_db)
    page = html.unescape(client.get(f"/prospects/{pid}/mail").text)
    assert "Réglages → Mail d'audit" in page and "disabled" in page


def test_C162_versions_of_the_shown_draft_travel_with_the_send(
    web: tuple[TestClient, Recorder], mail_db: Engine
) -> None:
    from prospection.storage.mail_send_log import all_sends

    client, _ = web
    pid = add_audited(mail_db)
    ready(mail_db)
    page = client.get(f"/prospects/{pid}/mail").text
    assert 'name="versions" value="o0-a' in page
    client.post(f"/prospects/{pid}/mail", headers=ORIGIN, data={
        "a": "contact@martin.fr", "objet": "Objet à moi", "texte": "Texte à moi",
        "versions": "o2-a-1-s1"})  # fmt: skip
    with mail_db.connect() as conn:
        [sent] = all_sends(conn)
    assert sent.structure == "courte" and sent.edited and sent.hook_version is None
