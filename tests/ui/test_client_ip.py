"""C83 : l'IP journalisée est celle que fournit Railway (X-Real-IP), pas une IP inventée."""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.storage.login_journal import recent_attempts
from prospection.ui.app import create_app

ORIGIN = {"Origin": "https://testserver"}


@pytest.fixture
def make_client(settings: Settings, engine: Engine) -> Iterator[Callable[[bool], TestClient]]:
    def build(behind_proxy: bool) -> TestClient:
        app = create_app(settings.model_copy(update={"behind_proxy": behind_proxy}), engine)
        return TestClient(app, base_url="https://testserver")

    yield build
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM login_attempts")


def last_ip(engine: Engine) -> str:
    with engine.connect() as conn:
        return recent_attempts(conn, 1)[0].ip


def test_C83_behind_railway_the_real_ip_header_is_used(
    make_client: Callable[[bool], TestClient], engine: Engine
) -> None:
    headers = {**ORIGIN, "X-Real-IP": "203.0.113.7", "X-Forwarded-For": "6.6.6.6"}
    make_client(True).post("/connexion", data={"mot_de_passe": "x"}, headers=headers)
    assert last_ip(engine) == "203.0.113.7"


def test_C83_without_proxy_the_headers_are_ignored(
    make_client: Callable[[bool], TestClient], engine: Engine
) -> None:
    headers = {**ORIGIN, "X-Real-IP": "6.6.6.6"}
    make_client(False).post("/connexion", data={"mot_de_passe": "x"}, headers=headers)
    assert last_ip(engine) == "testclient"
