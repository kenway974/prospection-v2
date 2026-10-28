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
    assert sent.url.path == "/sauvegardes/prospection-25.dump.chiffre"
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
