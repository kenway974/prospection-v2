"""Copie complète de la base (pg_dump) et restauration (pg_restore) pour C91. Le mot de passe
passe par l'environnement du programme, jamais par sa ligne de commande ni les journaux."""

import os
import subprocess

from sqlalchemy import make_url

DUMP_TIMEOUT = 600
UNKNOWN_TO_OLDER = (b"SET transaction_timeout",)  # réglages récents émis par pg_dump 17+


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


def _run(command: list[str], database_url: str | None, data: bytes | None = None) -> bytes:
    """`database_url` None : le programme ne se connecte pas (conversion de fichier)."""
    args, env = _libpq(database_url) if database_url else ([], dict(os.environ))
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
    """Remplace le contenu de la base par la copie, en une seule transaction (tout ou rien).
    La copie est d'abord convertie en SQL, sans les réglages qu'un serveur plus ancien ne
    connaît pas (pg_restore 17 vers PostgreSQL 16 : « transaction_timeout »)."""
    script = _run(["pg_restore", "--clean", "--if-exists", "--no-owner", "--no-privileges",
                   "--file=-"], None, data)  # fmt: skip
    psql = ["psql", "--quiet", "--no-psqlrc", "--single-transaction", "-v", "ON_ERROR_STOP=1"]
    _run(psql, database_url, for_older_servers(script))


def for_older_servers(script: bytes) -> bytes:
    lines = script.splitlines(keepends=True)
    return b"".join(line for line in lines if not line.startswith(UNKNOWN_TO_OLDER))
