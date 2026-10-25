"""C02 : saisie des clés ; C04 : jamais relues ailleurs que pour s'en servir."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import Engine

from prospection.application.api_keys import (
    EmptyKey,
    key_statuses,
    read_key,
    remove_key,
    store_key,
)
from prospection.domain.services import Service
from prospection.storage.secret_box import SecretBox

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
BOX = SecretBox(Fernet.generate_key().decode())


@pytest.fixture(autouse=True)
def clean(engine: Engine) -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM api_keys")


def test_C02_statuses_in_fixed_order_and_empty_by_default(engine: Engine) -> None:
    statuses = key_statuses(engine, BOX)
    assert [s.service for s in statuses] == [Service.GOOGLE, Service.NOTION, Service.INSEE]
    assert all(s.saved_at is None for s in statuses)


def test_C02_pasted_key_is_trimmed(engine: Engine) -> None:
    store_key(engine, BOX, Service.GOOGLE, "  AIza-123\n", NOW)
    assert read_key(engine, BOX, Service.GOOGLE) == "AIza-123"
    assert key_statuses(engine, BOX)[0].saved_at == NOW


def test_C02_empty_key_is_refused(engine: Engine) -> None:
    with pytest.raises(EmptyKey):
        store_key(engine, BOX, Service.GOOGLE, " \n ", NOW)


def test_unreadable_key_is_reported(engine: Engine) -> None:
    store_key(engine, BOX, Service.NOTION, "secret_1", NOW)
    other = SecretBox(Fernet.generate_key().decode())
    status = key_statuses(engine, other)[1]
    assert (status.saved_at, status.readable) == (NOW, False)
    assert read_key(engine, other, Service.NOTION) is None


def test_remove_key(engine: Engine) -> None:
    store_key(engine, BOX, Service.INSEE, "k", NOW)
    remove_key(engine, Service.INSEE)
    assert read_key(engine, BOX, Service.INSEE) is None
