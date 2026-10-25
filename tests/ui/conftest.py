"""Client de test de l'application web."""

from collections.abc import Iterator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine

from prospection.application.password import hash_password
from prospection.config import Settings
from prospection.ui.app import create_app

PASSWORD = "le bon mot de passe"


@pytest.fixture(scope="session")
def settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        session_secret=SecretStr("s" * 32),
        app_password_hash=SecretStr(hash_password(PASSWORD)),
        encryption_key=SecretStr(Fernet.generate_key().decode()),
    )


@pytest.fixture
def client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    with TestClient(create_app(settings, engine), base_url="https://testserver") as test_client:
        yield test_client
