"""C03 : tester une clé enregistrée et garder le résultat."""

from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import Engine

from prospection.application.api_keys import key_statuses, store_key
from prospection.application.key_tests import run_key_test
from prospection.domain.key_check import KeyCheck
from prospection.domain.services import Service
from prospection.storage.secret_box import SecretBox
from tests.fake_http import fake_client, json_reply

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
BOX = SecretBox(Fernet.generate_key().decode())


@pytest.fixture(autouse=True)
def clean(engine: Engine) -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")


def test_C03_result_is_recorded(engine: Engine) -> None:
    store_key(engine, BOX, Service.NOTION, "ntn_secret", NOW)
    client, recorder = fake_client(json_reply(200, {"object": "user"}))
    assert run_key_test(engine, BOX, Service.NOTION, client, NOW) == KeyCheck(
        True, "Jeton Notion valide."
    )
    assert recorder.requests[0].headers["Authorization"] == "Bearer ntn_secret"
    status = key_statuses(engine, BOX)[1]
    assert (status.tested_at, status.test_ok, status.test_message) == (
        NOW,
        True,
        "Jeton Notion valide.",
    )


def test_C03_test_without_key(engine: Engine) -> None:
    client, recorder = fake_client(json_reply(200, {}))
    assert run_key_test(engine, BOX, Service.GOOGLE, client, NOW) == KeyCheck(
        False, "Aucune clé enregistrée."
    )
    assert recorder.requests == []


def test_C03_test_unreadable_key(engine: Engine) -> None:
    store_key(engine, SecretBox(Fernet.generate_key().decode()), Service.INSEE, "k", NOW)
    client, _ = fake_client(json_reply(200, {}))
    assert run_key_test(engine, BOX, Service.INSEE, client, NOW) == KeyCheck(
        False, "Clé illisible : saisissez-la à nouveau."
    )


def test_C03_result_not_written_on_a_key_replaced_meanwhile(engine: Engine) -> None:
    store_key(engine, BOX, Service.GOOGLE, "ancienne", NOW)

    def replace_then_answer(request: httpx.Request) -> httpx.Response:
        store_key(engine, BOX, Service.GOOGLE, "nouvelle", NOW.replace(hour=9))
        return httpx.Response(200, json={"places": []})

    client, _ = fake_client(replace_then_answer)
    run_key_test(engine, BOX, Service.GOOGLE, client, NOW)
    status = key_statuses(engine, BOX)[0]
    assert (status.test_ok, status.test_message) == (None, None)
