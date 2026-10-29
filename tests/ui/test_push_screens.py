"""Notifications : écran Réglages → Rappels, abonnement du téléphone, essai."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.sources.web_push import generate_vapid_keys
from prospection.ui.app import create_app
from prospection.ui.deps import get_now
from prospection.ui.session import COOKIE_NAME, make_session_value
from tests.application.campaign_helpers import NOW
from tests.sources.test_web_push import ENDPOINT, phone
from tests.ui.test_call_screens import client, text
from tests.ui.test_search_form import ORIGIN

__all__ = ["client"]  # fixture partagée
PRIVATE, PUBLIC = generate_vapid_keys()


@pytest.fixture
def push_client(settings: Settings, campaign_db: Engine) -> Iterator[TestClient]:
    configured = settings.model_copy(update={
        "vapid_public_key": PUBLIC, "vapid_private_key": SecretStr(PRIVATE),
        "vapid_subject": "mailto:moi@example.fr",
    })  # fmt: skip
    app = create_app(configured, campaign_db)
    app.dependency_overrides[get_now] = lambda: NOW
    with TestClient(app, base_url="https://testserver") as test_client:
        test_client.cookies.set(COOKIE_NAME, make_session_value(configured, NOW))
        yield test_client


def test_not_configured_says_what_to_do(client: TestClient) -> None:
    assert "generate-vapid-keys" in text(client.get("/reglages/rappels"))


def test_phone_subscribes_then_test_notification(push_client: TestClient) -> None:
    page = text(push_client.get("/reglages/rappels"))
    assert f'data-vapid-key="{PUBLIC}"' in page and "Activer les notifications" in page
    _, p256dh, auth, _ = phone()
    body = {"endpoint": ENDPOINT, "keys": {"p256dh": p256dh, "auth": auth}}
    assert (
        push_client.post("/notifications/abonnement", json=body, headers=ORIGIN).status_code == 204
    )
    bad = push_client.post("/notifications/abonnement", json={"endpoint": "https://x.fr"},
                           headers=ORIGIN)  # fmt: skip
    assert bad.status_code == 400 and "non pris en charge" in bad.json()["erreur"]
    cross = push_client.post("/notifications/abonnement", json=body,
                             headers={"Origin": "https://evil.fr"})  # fmt: skip
    assert cross.status_code == 403
    gone = push_client.post("/notifications/desabonnement", json={"endpoint": ENDPOINT},
                            headers=ORIGIN)  # fmt: skip
    assert gone.status_code == 204
    tried = push_client.post("/notifications/essai", headers=ORIGIN, follow_redirects=False)
    assert tried.headers["location"] == "/reglages/rappels?essai=0"
    assert "Aucun téléphone" in text(push_client.get(tried.headers["location"]))


def test_quiet_hours_setting(client: TestClient) -> None:
    form = {"minutes": "15", "heure": "8", "calme_debut": "22", "calme_fin": "7"}
    client.post("/reglages/rappels", data=form, headers=ORIGIN)
    page = text(client.get("/reglages/rappels"))
    assert 'id="calme_debut" name="calme_debut" inputmode="numeric" value="22"' in page
    bad = client.post("/reglages/rappels", data={**form, "calme_fin": "30"}, headers=ORIGIN)
    assert bad.status_code == 400


def test_huge_body_refused_before_reading_it(push_client: TestClient) -> None:
    huge = b'{"endpoint": "' + b"x" * 10_000 + b'"}'
    answer = push_client.post("/notifications/abonnement", content=huge, headers={
        **ORIGIN, "Content-Type": "application/json"})  # fmt: skip
    assert answer.status_code == 413
    not_json = push_client.post("/notifications/abonnement", content=b"{", headers=ORIGIN)
    assert not_json.status_code == 400


def test_unreadable_vapid_key_refused_at_start(settings: Settings) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(**{**settings.model_dump(), "vapid_private_key": "mal copiée"})
