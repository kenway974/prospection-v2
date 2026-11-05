"""C143 : autorité du domaine, demandée une fois puis gardée 30 jours ; jamais bloquante."""

from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import Engine

from prospection.application.api_keys import store_key
from prospection.application.authority import domain_authority, known_authority
from prospection.domain.services import Service
from tests.application.campaign_helpers import BOX, NOW
from tests.fake_http import fake_client, json_reply, timeout
from tests.sources.test_open_pagerank import answer


@pytest.fixture(autouse=True)
def clean(engine: Engine) -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys; DELETE FROM domain_authority")


def test_C143_asked_once_then_kept_30_days(engine: Engine) -> None:
    store_key(engine, BOX, Service.OPENPAGERANK, "cle", NOW)
    client, recorder = fake_client(json_reply(200, answer("plombier.fr", 1.2)))
    assert domain_authority(engine, BOX, client, "plombier.fr", NOW) == 1.2
    assert domain_authority(engine, BOX, client, "plombier.fr", NOW + timedelta(days=29)) == 1.2
    assert len(recorder.requests) == 1
    assert known_authority(engine, "plombier.fr") == 1.2
    domain_authority(engine, BOX, client, "plombier.fr", NOW + timedelta(days=31))
    assert len(recorder.requests) == 2


def test_C143_without_key_or_when_down_nothing_is_said(engine: Engine) -> None:
    client, recorder = fake_client(json_reply(200, answer("plombier.fr", 1.2)))
    assert domain_authority(engine, BOX, client, "plombier.fr", NOW) is None
    assert not recorder.requests
    store_key(engine, BOX, Service.OPENPAGERANK, "cle", NOW)
    down, _ = fake_client(timeout)
    assert domain_authority(engine, BOX, down, "plombier.fr", NOW) is None
    assert known_authority(engine, "plombier.fr") is None  # rien gardé : redemandé plus tard
