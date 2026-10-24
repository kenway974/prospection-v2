"""Connexion par mot de passe (C01), limite d'essais (C82), journal (C83)."""

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Connection

from prospection.application.password import verify_password
from prospection.domain.login_throttle import WINDOW, check_login_allowed
from prospection.storage.login_journal import failures_since, record_attempt


class LoginOutcome(enum.Enum):
    OK = enum.auto()
    WRONG_PASSWORD = enum.auto()
    LOCKED = enum.auto()


@dataclass(frozen=True)
class LoginResult:
    outcome: LoginOutcome
    retry_after: timedelta


def attempt_login(
    conn: Connection, password_hash: str, plain: str, ip: str, now: datetime
) -> LoginResult:
    """Vérifie le mot de passe sauf si l'accès est bloqué ; journalise la tentative."""
    throttle = check_login_allowed(failures_since(conn, now - WINDOW), now)
    if not throttle.allowed:
        return LoginResult(LoginOutcome.LOCKED, throttle.retry_after)
    success = bool(plain) and verify_password(password_hash, plain)
    record_attempt(conn, now, ip, success)
    outcome = LoginOutcome.OK if success else LoginOutcome.WRONG_PASSWORD
    return LoginResult(outcome, timedelta(0))
