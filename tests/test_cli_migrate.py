"""Base injoignable au démarrage : message clair au lieu d'une trace Python."""

import pytest
from cryptography.fernet import Fernet

from prospection.application.password import hash_password
from prospection.cli import main


def test_migrate_with_unreachable_database_explains_what_to_do(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:1/x")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("APP_PASSWORD_HASH", hash_password("un mot de passe solide"))
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert main(["migrate"]) == 1
    out = capsys.readouterr().out
    assert "La base de données ne répond pas" in out
    assert "DATABASE_URL" in out
    assert "Traceback" not in out


def test_migrate_with_missing_variable_names_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main(["migrate"]) == 1
    assert "DATABASE_URL" in capsys.readouterr().out


def test_migrate_applies_migrations(
    monkeypatch: pytest.MonkeyPatch, database_url: str, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("APP_PASSWORD_HASH", hash_password("un mot de passe solide"))
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert main(["migrate"]) == 0


def test_C86_cli_generates_a_valid_fernet_key(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["generate-encryption-key"]) == 0
    key = capsys.readouterr().out.strip().splitlines()[-1]
    Fernet(key.encode())
