"""Copie complète de la base (pg_dump) et restauration (pg_restore) pour C91. Le mot de passe
passe par l'environnement du programme, jamais par sa ligne de commande ni les journaux."""

import os
import subprocess

from sqlalchemy import make_url

DUMP_TIMEOUT = 600


class BackupFailed(Exception):
    """pg_dump ou pg_restore a échoué ; le message ne contient aucun secret."""


def _libpq(database_url: str) -> tuple[list[str], dict[str, str]]:
    url = make_url(database_url)
    args = ["--host", url.host or "localhost", "--port", str(url.port or 5432),
            "--username", url.username or "postgres", "--dbname", url.database or ""]  # fmt: skip
    env = {**os.environ, "PGPASSWORD": url.password or "", "PGCONNECT_TIMEOUT": "10"}
    sslmode = url.query.get("sslmode")
    if isinstance(sslmode, str):
        env["PGSSLMODE"] = sslmode
    return args, env


def _run(command: list[str], database_url: str, data: bytes | None = None) -> bytes:
    args, env = _libpq(database_url)
    try:
        done = subprocess.run(  # noqa: S603 (programme fixe, arguments séparés)
            [*command, *args], input=data, env=env, capture_output=True, timeout=DUMP_TIMEOUT,
            check=False,
        )  # fmt: skip
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BackupFailed(f"{command[0]} : {type(error).__name__}") from None
    if done.returncode != 0:
        last = done.stderr.decode(errors="replace").strip().splitlines()[-1:] or ["?"]
        raise BackupFailed(f"{command[0]} : {last[0][:200]}")
    return done.stdout


def dump_database(database_url: str) -> bytes:
    return _run(["pg_dump", "--format=custom", "--no-owner", "--no-privileges"], database_url)


def restore_database(database_url: str, data: bytes) -> None:
    """Remplace le contenu de la base par la copie (une seule transaction : tout ou rien)."""
    command = ["pg_restore", "--clean", "--if-exists", "--no-owner", "--no-privileges",
               "--single-transaction"]  # fmt: skip
    _run(command, database_url, data)
