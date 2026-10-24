"""C83 : journal des connexions ; C82 : échecs récents."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection

from prospection.storage.login_journal import (
    LoginAttempt,
    failures_since,
    recent_attempts,
    record_attempt,
)

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=UTC)


def test_C83_attempts_are_recorded_with_date_ip_and_result(conn: Connection) -> None:
    record_attempt(conn, NOW - timedelta(minutes=2), "1.1.1.1", success=False)
    record_attempt(conn, NOW - timedelta(minutes=1), "2.2.2.2", success=True)
    record_attempt(conn, NOW - timedelta(minutes=3), "3.3.3.3", success=False)
    assert recent_attempts(conn, 10) == [
        LoginAttempt(NOW - timedelta(minutes=1), "2.2.2.2", True),
        LoginAttempt(NOW - timedelta(minutes=2), "1.1.1.1", False),
        LoginAttempt(NOW - timedelta(minutes=3), "3.3.3.3", False),
    ]


def test_C83_recent_attempts_respects_limit(conn: Connection) -> None:
    for minutes in range(5):
        record_attempt(conn, NOW - timedelta(minutes=minutes), "1.1.1.1", success=True)
    assert len(recent_attempts(conn, 2)) == 2


def test_C82_failures_since_ignores_successes_and_old_attempts(conn: Connection) -> None:
    record_attempt(conn, NOW - timedelta(minutes=20), "1.1.1.1", success=False)
    record_attempt(conn, NOW - timedelta(minutes=5), "1.1.1.1", success=False)
    record_attempt(conn, NOW - timedelta(minutes=1), "1.1.1.1", success=True)
    assert failures_since(conn, NOW - timedelta(minutes=15)) == [NOW - timedelta(minutes=5)]
