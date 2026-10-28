"""Fixtures communes : base PostgreSQL de test, créée puis supprimée."""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, make_url, text

from prospection.application.api_keys import store_key
from prospection.domain.services import Service
from tests.application.campaign_helpers import BOX as CAMPAIGN_BOX
from tests.application.campaign_helpers import NOW as CAMPAIGN_NOW
from tests.application.campaign_helpers import TABLES as CAMPAIGN_TABLES

SERVER_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
)
MIGRATIONS = Path(__file__).parent.parent / "src" / "prospection" / "storage" / "migrations"


def alembic_config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    name = f"prospection_test_{uuid.uuid4().hex[:12]}"
    server = create_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(SERVER_URL).set(database=name).render_as_string(hide_password=False)
    try:
        yield url
    finally:
        with server.connect() as conn:
            conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        server.dispose()


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    command.upgrade(alembic_config(database_url), "head")
    eng = create_engine(database_url)
    yield eng
    eng.dispose()


@pytest.fixture
def conn(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture
def campaign_db(engine: Engine) -> Iterator[Engine]:
    store_key(engine, CAMPAIGN_BOX, Service.GOOGLE, "AIza-test", CAMPAIGN_NOW)
    yield engine
    with engine.begin() as conn:
        conn.exec_driver_sql(f"TRUNCATE {CAMPAIGN_TABLES}, crm_index RESTART IDENTITY CASCADE")
        conn.exec_driver_sql(
            "UPDATE app_settings SET google_budget_cents = NULL, crm = 'none', "
            "notion_database_id = NULL, notion_database_title = NULL"
        )


@pytest.fixture(autouse=True)
def notion_without_pause() -> Iterator[None]:
    """Le rythme réel de Notion (C75) est testé à part : ici, pas d'attente."""
    from prospection.crm import notion_http as notion_pages

    interval = notion_pages.PACER.interval
    notion_pages.PACER.interval = 0
    yield
    notion_pages.PACER.interval = interval
