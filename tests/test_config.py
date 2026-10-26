"""Une variable d'environnement manquante est nommée dans l'erreur."""

import pytest
from cryptography.fernet import Fernet

from prospection.application.password import hash_password
from prospection.config import ConfigError, load_settings

VALID_HASH = hash_password("un mot de passe solide")
FERNET_KEY = Fernet.generate_key().decode()


def test_missing_variable_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("APP_PASSWORD_HASH", VALID_HASH)
    monkeypatch.setenv("ENCRYPTION_KEY", FERNET_KEY)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(ConfigError, match="SESSION_SECRET"):
        load_settings()


def test_short_session_secret_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("APP_PASSWORD_HASH", VALID_HASH)
    monkeypatch.setenv("SESSION_SECRET", "court")
    monkeypatch.setenv("ENCRYPTION_KEY", FERNET_KEY)
    with pytest.raises(ConfigError, match="SESSION_SECRET"):
        load_settings()


def test_malformed_password_hash_is_refused_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("APP_PASSWORD_HASH", '"$argon2id$tronqué"')
    monkeypatch.setenv("ENCRYPTION_KEY", FERNET_KEY)
    with pytest.raises(ConfigError, match="APP_PASSWORD_HASH"):
        load_settings()


def test_default_timezone_is_paris(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("APP_PASSWORD_HASH", VALID_HASH)
    monkeypatch.setenv("ENCRYPTION_KEY", FERNET_KEY)
    monkeypatch.delenv("TIMEZONE", raising=False)
    assert load_settings().timezone == "Europe/Paris"


def set_valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("APP_PASSWORD_HASH", VALID_HASH)


def test_C86_encryption_key_comes_from_environment_only(monkeypatch: pytest.MonkeyPatch) -> None:
    set_valid_env(monkeypatch)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(ConfigError, match="ENCRYPTION_KEY"):
        load_settings()


def test_C86_invalid_encryption_key_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    set_valid_env(monkeypatch)
    monkeypatch.setenv("ENCRYPTION_KEY", "pas-une-cle-fernet")
    with pytest.raises(ConfigError, match="ENCRYPTION_KEY"):
        load_settings()


def test_test_services_url_accepted_only_locally_without_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_valid_env(monkeypatch)
    monkeypatch.setenv("ENCRYPTION_KEY", FERNET_KEY)
    monkeypatch.setenv("BEHIND_PROXY", "false")
    monkeypatch.setenv("TEST_SERVICES_URL", "http://127.0.0.1:8099")
    assert load_settings().test_services_url == "http://127.0.0.1:8099"


@pytest.mark.parametrize(
    ("behind_proxy", "url"),
    [("true", "http://127.0.0.1:8099"), ("false", "https://espion.example"),
     ("false", "http://10.0.0.5:8099"), ("false", "ftp://localhost:21")],
)  # fmt: skip
def test_test_services_url_refused_in_production_or_remote(
    monkeypatch: pytest.MonkeyPatch, behind_proxy: str, url: str
) -> None:
    set_valid_env(monkeypatch)
    monkeypatch.setenv("ENCRYPTION_KEY", FERNET_KEY)
    monkeypatch.setenv("BEHIND_PROXY", behind_proxy)
    monkeypatch.setenv("TEST_SERVICES_URL", url)
    with pytest.raises(ConfigError, match="TEST_SERVICES_URL"):
        load_settings()
