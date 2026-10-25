"""Connexion par mot de passe (C01), limite d'essais (C82), journal (C83)."""

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Connection

from prospection.application.password import verify_password
from prospection.domain.login_throttle import WINDOW, check_login_allowed
from prospection.storage.login_journal import (
    delete_attempts_before,
    failures_since,
    has_blocked_since,
    has_success_since,
    lock_login_attempts,
    record_attempt,
)

KNOWN_IP_PERIOD = timedelta(days=90)
JOURNAL_RETENTION = timedelta(days=90)
BLOCKED_LOG_INTERVAL = timedelta(minutes=1)


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
    """Vérifie le mot de passe sauf si l'accès est bloqué ; journalise chaque tentative.

    Le verrou rend « vérifier puis enregistrer » atomique : des tentatives
    simultanées ne peuvent pas dépasser la limite. L'appelant valide la transaction.
    """
    lock_login_attempts(conn)
    delete_attempts_before(conn, now - JOURNAL_RETENTION)
    since = now - WINDOW
    known_ip = has_success_since(conn, ip, now - KNOWN_IP_PERIOD)
    throttle = check_login_allowed(
        failures_since(conn, since, ip=ip), failures_since(conn, since), now, known_ip
    )
    if not throttle.allowed:
        # Une ligne par IP et par minute au plus : le journal ne peut pas être inondé.
        if not has_blocked_since(conn, ip, now - BLOCKED_LOG_INTERVAL):
            record_attempt(conn, now, ip, success=False, blocked=True)
        return LoginResult(LoginOutcome.LOCKED, throttle.retry_after)
    success = bool(plain) and verify_password(password_hash, plain)
    record_attempt(conn, now, ip, success)
    outcome = LoginOutcome.OK if success else LoginOutcome.WRONG_PASSWORD
    return LoginResult(outcome, timedelta(0))
