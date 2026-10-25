"""C82 : des tentatives simultanées ne contournent pas la limite d'essais."""

import threading
from datetime import UTC, datetime

from sqlalchemy import Engine

from prospection.application.login import attempt_login
from prospection.storage.login_journal import lock_login_attempts

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=UTC)


def test_C82_attempts_are_serialized(engine: Engine) -> None:
    finished = threading.Event()

    def other_attempt() -> None:
        with engine.begin() as conn:
            attempt_login(conn, "pas-un-hash", "faux", "9.9.9.9", NOW)
        finished.set()

    with engine.connect() as holder:
        transaction = holder.begin()
        lock_login_attempts(holder)
        thread = threading.Thread(target=other_attempt)
        thread.start()
        assert not finished.wait(0.5), "la tentative aurait dû attendre le verrou"
        transaction.rollback()
    thread.join(5)
    assert finished.is_set()
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM login_attempts WHERE ip = '9.9.9.9'")
