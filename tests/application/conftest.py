"""Fixtures des tests de l'application."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from prospection.application.api_keys import store_key
from prospection.domain.services import Service
from tests.application.campaign_helpers import BOX, NOW, TABLES


@pytest.fixture
def campaign_db(engine: Engine) -> Iterator[Engine]:
    store_key(engine, BOX, Service.GOOGLE, "AIza-test", NOW)
    yield engine
    with engine.begin() as conn:
        conn.exec_driver_sql(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
        conn.exec_driver_sql("UPDATE app_settings SET google_budget_cents = NULL")
