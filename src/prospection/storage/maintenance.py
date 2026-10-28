"""Traces de maintenance : vérification des vraies API (C99) et sauvegarde (C91)."""

from datetime import datetime, timedelta

from sqlalchemy import Connection, select, update

from prospection.storage.db import app_settings

_S = app_settings.c


def claim_api_check(conn: Connection, now: datetime, every: timedelta) -> bool:
    """Vrai si la vérification est due ; la date est posée aussitôt (une seule fois)."""
    due = _S.api_checked_at.is_(None) | (_S.api_checked_at <= now - every)
    query = update(app_settings).where(_S.id == 1, due).values(api_checked_at=now)
    return conn.execute(query.returning(_S.id)).first() is not None


def note_api_outage(conn: Connection, retry_at: datetime, every: timedelta) -> int:
    """Panne passagère : nouvel essai à `retry_at` ; renvoie combien de suite (1, 2…)."""
    row = conn.execute(
        update(app_settings).where(_S.id == 1)
        .values(api_failures=_S.api_failures + 1, api_checked_at=retry_at - every)
        .returning(_S.api_failures)
    ).one()  # fmt: skip
    return int(row[0])


def reset_api_outages(conn: Connection) -> None:
    conn.execute(update(app_settings).where(_S.id == 1).values(api_failures=0))


def last_backup(conn: Connection) -> tuple[datetime | None, str | None]:
    row = conn.execute(select(_S.backup_at, _S.backup_error).where(_S.id == 1)).one()
    return row.backup_at, row.backup_error


def record_backup(conn: Connection, now: datetime, error: str | None) -> None:
    """Réussite : date et plus d'erreur ; échec : l'erreur, la dernière réussite gardée."""
    values: dict[str, object] = {"backup_error": error}
    if error is None:
        values["backup_at"] = now
    conn.execute(update(app_settings).where(_S.id == 1).values(**values))
