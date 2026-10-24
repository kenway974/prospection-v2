"""Une variable d'environnement manquante est nommée dans l'erreur."""

import pytest

from prospection.config import ConfigError, load_settings


def test_missing_variable_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("APP_PASSWORD_HASH", "$argon2id$x")
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(ConfigError, match="SESSION_SECRET"):
        load_settings()


def test_short_session_secret_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/x")
    monkeypatch.setenv("APP_PASSWORD_HASH", "$argon2id$x")
    monkeypatch.setenv("SESSION_SECRET", "court")
    with pytest.raises(ConfigError, match="SESSION_SECRET"):
        load_settings()
