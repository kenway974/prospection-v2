"""C91 : restauration d'une sauvegarde en ligne de commande, avec confirmation."""

from pathlib import Path
from unittest import mock

import pytest
from cryptography.fernet import Fernet

from prospection.application.password import hash_password
from prospection.cli import main, restore_backup

KEY = Fernet.generate_key().decode()


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:1/x")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("APP_PASSWORD_HASH", hash_password("un mot de passe solide"))
    monkeypatch.setenv("ENCRYPTION_KEY", KEY)


def test_C91_wrong_key_or_missing_file_says_so(
    env: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    other = tmp_path / "autre.dump.chiffre"
    other.write_bytes(Fernet(Fernet.generate_key()).encrypt(b"copie"))
    assert main(["restore-backup", str(other)]) == 1
    assert "ENCRYPTION_KEY" in capsys.readouterr().out
    assert main(["restore-backup", str(tmp_path / "absent")]) == 1


def test_C91_nothing_changes_without_confirmation(
    env: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "prospection-28.dump.chiffre"
    copy.write_bytes(Fernet(KEY.encode()).encrypt(b"copie"))
    with mock.patch("prospection.storage.backup_dump.restore_database") as restore:
        assert restore_backup(str(copy), ask=lambda _: "non") == 1
        restore.assert_not_called()
    assert "Rien n'a été changé" in capsys.readouterr().out
    assert restore_backup(str(copy), ask=lambda _: "RESTAURER") == 1  # base injoignable
    assert "base inchangée" in capsys.readouterr().out
