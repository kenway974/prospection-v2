"""C01 : accès par mot de passe ; C82 : limite d'essais ; C83 : journal."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Connection

from prospection.application.login import LoginOutcome, LoginResult, attempt_login
from prospection.application.password import hash_password
from prospection.storage.login_journal import recent_attempts

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=UTC)
GOOD = "le bon mot de passe"


@pytest.fixture(scope="module")
def password_hash() -> str:
    return hash_password(GOOD)


def test_C01_correct_password_logs_in_and_is_journaled(
    conn: Connection, password_hash: str
) -> None:
    result = attempt_login(conn, password_hash, GOOD, "1.1.1.1", NOW)
    assert result == LoginResult(LoginOutcome.OK, timedelta(0))
    assert recent_attempts(conn, 1)[0].success is True


def test_C01_wrong_password_is_refused_and_journaled(conn: Connection, password_hash: str) -> None:
    result = attempt_login(conn, password_hash, "faux", "1.1.1.1", NOW)
    assert result.outcome is LoginOutcome.WRONG_PASSWORD
    attempt = recent_attempts(conn, 1)[0]
    assert (attempt.ip, attempt.success) == ("1.1.1.1", False)


def test_C01_empty_password_is_refused(conn: Connection, password_hash: str) -> None:
    assert attempt_login(conn, password_hash, "", "1.1.1.1", NOW).outcome is (
        LoginOutcome.WRONG_PASSWORD
    )


def test_C82_locked_after_five_failures_even_with_right_password(
    conn: Connection, password_hash: str
) -> None:
    for i in range(5):
        attempt_login(conn, password_hash, "faux", "1.1.1.1", NOW + timedelta(seconds=i))
    result = attempt_login(conn, password_hash, GOOD, "1.1.1.1", NOW + timedelta(minutes=1))
    assert result == LoginResult(LoginOutcome.LOCKED, timedelta(minutes=15))


def test_C82_another_ip_cannot_lock_out_the_owner(conn: Connection, password_hash: str) -> None:
    for i in range(5):
        attempt_login(conn, password_hash, "faux", "6.6.6.6", NOW + timedelta(seconds=i))
    result = attempt_login(conn, password_hash, GOOD, "1.1.1.1", NOW + timedelta(minutes=1))
    assert result.outcome is LoginOutcome.OK


def test_C82_many_ips_trigger_the_global_ceiling(conn: Connection, password_hash: str) -> None:
    for i in range(50):
        attempt_login(conn, password_hash, "faux", f"10.0.0.{i}", NOW + timedelta(seconds=i))
    result = attempt_login(conn, password_hash, GOOD, "1.1.1.1", NOW + timedelta(minutes=1))
    assert result.outcome is LoginOutcome.LOCKED


def test_C83_blocked_attempts_are_journaled_without_extending_the_block(
    conn: Connection, password_hash: str
) -> None:
    for i in range(5):
        attempt_login(conn, password_hash, "faux", "6.6.6.6", NOW + timedelta(seconds=i))
    attempt_login(conn, password_hash, "faux", "6.6.6.6", NOW + timedelta(minutes=10))
    last = recent_attempts(conn, 1)[0]
    assert (last.ip, last.success, last.blocked) == ("6.6.6.6", False, True)
    later = attempt_login(conn, password_hash, GOOD, "6.6.6.6", NOW + timedelta(minutes=16))
    assert later.outcome is LoginOutcome.OK
