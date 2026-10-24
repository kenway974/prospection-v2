"""C82 : mot de passe haché (argon2)."""

import pytest

from prospection.application.password import hash_password, verify_password
from prospection.cli import main


def test_C82_password_is_hashed_and_verifiable() -> None:
    hashed = hash_password("un mot de passe solide")
    assert hashed.startswith("$argon2id$")
    assert "solide" not in hashed
    assert verify_password(hashed, "un mot de passe solide") is True
    assert verify_password(hashed, "autre chose") is False


def test_verify_password_with_malformed_hash_is_false() -> None:
    assert verify_password("pas-un-hash", "x") is False


def test_cli_refuses_short_password(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("prospection.cli.getpass", lambda prompt="": "court")
    assert main(["hash-password"]) == 1
    assert "Choisissez au moins 12 caractères." in capsys.readouterr().out


def test_cli_refuses_mismatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["un mot de passe solide", "un autre mot de passe"])
    monkeypatch.setattr("prospection.cli.getpass", lambda prompt="": next(answers))
    assert main(["hash-password"]) == 1
    assert "Les deux saisies sont différentes." in capsys.readouterr().out


def test_cli_prints_hash(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("prospection.cli.getpass", lambda prompt="": "un mot de passe solide")
    assert main(["hash-password"]) == 0
    out = capsys.readouterr().out
    hashed = next(line for line in out.splitlines() if line.startswith("$argon2id$"))
    assert verify_password(hashed, "un mot de passe solide")
