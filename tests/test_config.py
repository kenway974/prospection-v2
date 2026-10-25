"""Une variable d'environnement manquante est nommée dans l'erreur."""

import pytest

from prospection.application.password import hash_password
from prospection.config import ConfigError, load_settings

VALID_HASH = hash_password("un mot de passe solide")


def test_missing_variable_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("APP_PASSWORD_HASH", VALID_HASH)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(ConfigError, match="SESSION_SECRET"):
        load_settings()


def test_short_session_secret_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("APP_PASSWORD_HASH", VALID_HASH)
    monkeypatch.setenv("SESSION_SECRET", "court")
    with pytest.raises(ConfigError, match="SESSION_SECRET"):
        load_settings()


def test_malformed_password_hash_is_refused_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("APP_PASSWORD_HASH", '"$argon2id$tronqué"')
    with pytest.raises(ConfigError, match="APP_PASSWORD_HASH"):
        load_settings()


def test_default_timezone_is_paris(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("APP_PASSWORD_HASH", VALID_HASH)
    monkeypatch.delenv("TIMEZONE", raising=False)
    assert load_settings().timezone == "Europe/Paris"
