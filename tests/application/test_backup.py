"""C91 : sauvegarde quotidienne chiffrée, échec signalé."""

from datetime import timedelta

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import Engine

from prospection.application.backup import BackupTarget, daily_backup, read_backup
from prospection.storage.alerts import unseen_alerts
from prospection.storage.backup_dump import BackupFailed
from prospection.storage.maintenance import last_backup
from tests.application.campaign_helpers import NOW
from tests.fake_http import fake_client

KEY = Fernet.generate_key().decode()
TARGET = BackupTarget("https://acct.r2.cloudflarestorage.com/sauvegardes", "AKID", "secret")


def test_C91_daily_encrypted_copy(campaign_db: Engine) -> None:
    client, seen = fake_client(lambda r: httpx.Response(200))
    assert daily_backup(campaign_db, TARGET, KEY, lambda: b"copie", client, NOW)
    [sent] = seen.requests
    assert (
        sent.url.path == f"/sauvegardes/prospection-{NOW.date().toordinal() % 30:02d}.dump.chiffre"
    )
    assert b"copie" not in sent.content and read_backup(KEY, sent.content) == b"copie"
    assert not daily_backup(
        campaign_db, TARGET, KEY, lambda: b"copie", client, NOW + timedelta(hours=5)
    )
    assert daily_backup(campaign_db, TARGET, KEY, lambda: b"copie", client, NOW + timedelta(days=1))
    with campaign_db.connect() as conn:
        assert last_backup(conn) == (NOW + timedelta(days=1), None)
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        read_backup(Fernet.generate_key().decode(), sent.content)


def test_C91_failure_kept_and_alerted(campaign_db: Engine) -> None:
    def broken() -> bytes:
        raise BackupFailed("pg_dump : connexion refusée")

    client, seen = fake_client(lambda r: httpx.Response(200))
    assert daily_backup(campaign_db, TARGET, KEY, broken, client, NOW)
    assert seen.requests == []
    with campaign_db.connect() as conn:
        [alert] = unseen_alerts(conn)
        assert last_backup(conn) == (None, "pg_dump : connexion refusée")
    assert "Sauvegarde de la base échouée" in alert.message


def test_C91_thirty_rotating_names() -> None:
    from prospection.application.backup import backup_name

    names = {backup_name(NOW + timedelta(days=n)) for n in range(60)}
    assert len(names) == 30 and backup_name(NOW) == backup_name(NOW + timedelta(days=30))


def test_C91_backup_runs_aside_and_never_twice_at_once(campaign_db: Engine) -> None:
    import threading

    from prospection.application.backup import backup_job

    started, release = threading.Event(), threading.Event()

    def slow_put(request: httpx.Request) -> httpx.Response:
        started.set()
        release.wait(5)
        return httpx.Response(200)

    client, seen = fake_client(slow_put)
    job = backup_job(TARGET, KEY, "postgresql+psycopg://u:p@127.0.0.1:1/x", campaign_db, client)
    assert job is not None and backup_job(None, KEY, "", campaign_db, client) is None
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("prospection.application.backup.dump_database", lambda url: b"copie")
        assert job(NOW) is True and started.wait(5)  # rend la main tout de suite
        assert job(NOW) is False  # déjà en cours
        release.set()
        for _ in range(50):
            if job(NOW + timedelta(days=1)) is not False:
                break
            threading.Event().wait(0.05)
    assert len(seen.requests) >= 1
