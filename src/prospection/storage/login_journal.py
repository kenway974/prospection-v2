"""Journal des tentatives de connexion (C82, C83)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, insert, select, text

from prospection.storage.db import login_attempts

LOGIN_LOCK_KEY = 9740001


@dataclass(frozen=True)
class LoginAttempt:
    at: datetime
    ip: str
    success: bool


def lock_login_attempts(conn: Connection) -> None:
    """Sérialise les tentatives jusqu'à la fin de la transaction en cours."""
    conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LOGIN_LOCK_KEY})


def record_attempt(conn: Connection, at: datetime, ip: str, success: bool) -> None:
    conn.execute(insert(login_attempts).values(at=at, ip=ip, success=success))


def failures_since(conn: Connection, since: datetime) -> list[datetime]:
    query = (
        select(login_attempts.c.at)
        .where(login_attempts.c.at >= since, login_attempts.c.success.is_(False))
        .order_by(login_attempts.c.at)
    )
    return list(conn.scalars(query))


def recent_attempts(conn: Connection, limit: int) -> list[LoginAttempt]:
    query = (
        select(login_attempts.c.at, login_attempts.c.ip, login_attempts.c.success)
        .order_by(login_attempts.c.at.desc())
        .limit(limit)
    )
    return [LoginAttempt(row.at, row.ip, row.success) for row in conn.execute(query)]
