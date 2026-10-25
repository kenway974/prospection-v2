"""Lecture du journal des connexions (C83)."""

from sqlalchemy import Engine

from prospection.storage.login_journal import LoginAttempt, recent_attempts

JOURNAL_SIZE = 50


def latest_attempts(engine: Engine) -> list[LoginAttempt]:
    with engine.connect() as conn:
        return recent_attempts(conn, JOURNAL_SIZE)
