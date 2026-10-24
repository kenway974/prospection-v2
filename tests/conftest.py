"""Fixtures communes : base PostgreSQL de test, créée puis supprimée."""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, make_url, text

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
