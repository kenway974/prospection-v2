"""Journal des tentatives de connexion (C82, C83)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, delete, exists, insert, select, text

from prospection.storage.db import login_attempts

LOGIN_LOCK_KEY = 9740001


@dataclass(frozen=True)
class LoginAttempt:
    at: datetime
    ip: str
    success: bool
    blocked: bool


def lock_login_attempts(conn: Connection) -> None:
    """Sérialise les tentatives jusqu'à la fin de la transaction en cours."""
    conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOGIN_LOCK_KEY})


def record_attempt(
    conn: Connection, at: datetime, ip: str, success: bool, blocked: bool = False
) -> None:
    values = {"at": at, "ip": ip, "success": success, "blocked": blocked}
    conn.execute(insert(login_attempts).values(**values))


def failures_since(conn: Connection, since: datetime, ip: str | None = None) -> list[datetime]:
    """Échecs vérifiés depuis `since` (les essais refusés pendant un blocage ne comptent pas)."""
    query = select(login_attempts.c.at).where(
        login_attempts.c.at >= since,
        login_attempts.c.success.is_(False),
        login_attempts.c.blocked.is_(False),
    )
    if ip is not None:
        query = query.where(login_attempts.c.ip == ip)
    return list(conn.scalars(query.order_by(login_attempts.c.at)))


def recent_attempts(conn: Connection, limit: int) -> list[LoginAttempt]:
    columns = login_attempts.c
    query = (
        select(columns.at, columns.ip, columns.success, columns.blocked)
        .order_by(columns.at.desc())
        .limit(limit)
    )
    return [LoginAttempt(r.at, r.ip, r.success, r.blocked) for r in conn.execute(query)]


def has_success_since(conn: Connection, ip: str, since: datetime) -> bool:
    c = login_attempts.c
    query = select(exists().where(c.ip == ip, c.success.is_(True), c.at >= since))
    return bool(conn.scalar(query))


def has_blocked_since(conn: Connection, ip: str, since: datetime) -> bool:
    c = login_attempts.c
    query = select(exists().where(c.ip == ip, c.blocked.is_(True), c.at > since))
    return bool(conn.scalar(query))


def delete_attempts_before(conn: Connection, before: datetime) -> None:
    conn.execute(delete(login_attempts).where(login_attempts.c.at < before))
