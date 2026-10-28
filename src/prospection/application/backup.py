"""Sauvegarde quotidienne de la base (C91) : copie chiffrée (clé ENCRYPTION_KEY) déposée sur
un stockage compatible S3 ; 30 emplacements tournants, donc exactement 30 jours gardés."""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import Engine

from prospection.sources.object_storage import UploadFailed, put_object
from prospection.storage.alerts import add_alert
from prospection.storage.backup_dump import BackupFailed, dump_database
from prospection.storage.maintenance import last_backup, record_backup

logger = logging.getLogger(__name__)

KEPT_DAYS = 30


@dataclass(frozen=True)
class BackupTarget:
    url: str  # https://<compte>.r2.cloudflarestorage.com/<seau>
    access_key: str
    secret_key: str
    region: str = "auto"


def backup_name(now: datetime) -> str:
    """Le même nom revient tous les 30 jours : la copie d'il y a 30 jours est remplacée."""
    return f"prospection-{now.date().toordinal() % KEPT_DAYS:02d}.dump.chiffre"


def daily_backup(
    engine: Engine, target: BackupTarget, encryption_key: str, dump: Callable[[], bytes],
    client: httpx.Client, now: datetime,
) -> bool:  # fmt: skip
    """Vrai si une sauvegarde a été tentée ; un échec est gardé et signalé par une alerte."""
    with engine.connect() as conn:
        done_at, _ = last_backup(conn)
    if done_at is not None and done_at.date() == now.date():  # une par jour (UTC)
        return False
    try:
        data = Fernet(encryption_key.encode()).encrypt(dump())
        url = f"{target.url.rstrip('/')}/{backup_name(now)}"
        put_object(client, url, data, target.access_key, target.secret_key, target.region, now)
    except (BackupFailed, UploadFailed) as error:
        with engine.begin() as conn:
            record_backup(conn, now, str(error))
            message = f"Sauvegarde de la base échouée : {error}. Nouvel essai dans une heure."
            add_alert(conn, f"sauvegarde:{now:%Y-%m-%d}", "sauvegarde", message,
                      "/tableau-de-bord", now)  # fmt: skip
        return True
    with engine.begin() as conn:
        record_backup(conn, now, None)
    return True


def read_backup(encryption_key: str, data: bytes) -> bytes:
    """Copie déchiffrée, prête pour pg_restore ; ValueError si la clé ne correspond pas."""
    try:
        return Fernet(encryption_key.encode()).decrypt(data)
    except Exception:
        raise ValueError("Fichier illisible avec cette ENCRYPTION_KEY.") from None


def backup_job(
    target: BackupTarget | None, encryption_key: str, database_url: str, engine: Engine,
    client: httpx.Client,
) -> Callable[[datetime], object] | None:  # fmt: skip
    """Travail régulier de la tâche de fond, si le stockage est configuré ; sinon rien."""
    if target is None:
        return None
    configured, running = target, threading.Lock()

    def work(now: datetime) -> None:
        try:
            dump = lambda: dump_database(database_url)  # noqa: E731
            daily_backup(engine, configured, encryption_key, dump, client, now)
        except Exception:
            logger.exception("Sauvegarde en échec")
        finally:
            running.release()

    def run(now: datetime) -> object:
        """Dans un fil à part : pg_dump peut durer, les rappels ne doivent pas attendre."""
        if not running.acquire(blocking=False):
            return False
        threading.Thread(target=work, args=(now,), name="sauvegarde", daemon=True).start()
        return True

    return run
