"""C91, C94, C99 : travaux réguliers isolés ; sauvegarde configurée ou non."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from prospection.application.periodic import Periodic
from prospection.config import Settings

NOW = datetime(2026, 10, 28, 3, tzinfo=UTC)


def test_regular_job_runs_at_its_pace_and_never_breaks_the_worker() -> None:
    calls: list[datetime] = []

    def flaky(now: datetime) -> None:
        calls.append(now)
        raise RuntimeError("panne")

    job = Periodic("essai", timedelta(hours=1), flaky)
    job.maybe_run(NOW)  # l'erreur est journalisée, pas propagée
    job.maybe_run(NOW + timedelta(minutes=30))
    job.maybe_run(NOW + timedelta(hours=1))
    assert calls == [NOW, NOW + timedelta(hours=1)]


def _settings(**values: str) -> Settings:
    from cryptography.fernet import Fernet

    from prospection.application.password import hash_password

    base = {"database_url": "postgresql+psycopg://u:p@h/b", "session_secret": "s" * 32,
            "app_password_hash": hash_password("un mot de passe solide"),
            "encryption_key": Fernet.generate_key().decode()}  # fmt: skip
    return Settings(**base, **values)  # type: ignore[arg-type]


def test_C91_backup_only_when_fully_configured() -> None:
    assert _settings().backup_target() is None
    assert _settings(backup_s3_url="https://a.r2.cloudflarestorage.com/s").backup_target() is None
    full = _settings(backup_s3_url="https://a.r2.cloudflarestorage.com/s",
                     backup_s3_access_key="AKID", backup_s3_secret_key="secret")  # fmt: skip
    target = full.backup_target()
    assert target is not None and target.region == "auto"
    with pytest.raises(ValidationError):
        _settings(backup_s3_url="http://a.example/s")


def test_push_only_when_fully_configured() -> None:
    assert _settings().vapid_keys() is None
    keys = _settings(vapid_public_key="pub", vapid_private_key="priv",
                     vapid_subject="mailto:moi@example.fr").vapid_keys()  # fmt: skip
    assert keys is not None and keys.public_key == "pub"
    with pytest.raises(ValidationError):
        _settings(vapid_subject="moi@example.fr")
