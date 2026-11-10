"""C169, C170 : la tâche de fond envoie la file sans relecture, au bon rythme, et s'arrête
après trois refus de Gmail de suite."""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from prospection.application.mail_batch import queue_batch
from prospection.application.mail_queue_run import send_next
from prospection.storage.mail_queue import pending_ids
from prospection.storage.mail_queue_settings import paused, save_daily_limit, set_paused
from tests.application.campaign_helpers import BOX
from tests.application.mail_helpers import BASE, OAUTH, add_audited, google, ready

TUESDAY = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)  # 10 h à Paris
TZ = "Europe/Paris"


def _run(engine: Engine, now: datetime = TUESDAY, status: int = 200) -> tuple[bool, int]:
    client, recorder = google(status)
    done = send_next(engine, BOX, client, OAUTH, BASE, now, TZ, random.Random(0))  # noqa: S311 (attente tirée, rejouable)
    return done, sum(1 for r in recorder.requests if "gmail" in r.url.host)


def _statuses(engine: Engine) -> list[tuple[str, str | None]]:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("SELECT status, reason FROM mail_queue ORDER BY id")
        return [(r.status, r.reason) for r in rows]


def _queue(engine: Engine, *emails: str) -> list[int]:
    ids = [add_audited(engine, contacts_email=e) for e in emails]
    queue_batch(engine, BOX, ids, TUESDAY)
    return ids


def test_C169_oldest_first_with_note_and_reminder(mail_db: Engine) -> None:
    ready(mail_db)
    first, _ = _queue(mail_db, "a@martin.fr", "b@martin.fr")
    assert _run(mail_db) == (True, 1)
    assert _statuses(mail_db)[0] == ("envoye", None)
    with mail_db.connect() as conn:
        notes = conn.exec_driver_sql(
            "SELECT count(*) FROM prospect_notes WHERE prospect_id = %(p)s", {"p": first}
        ).scalar_one()
    assert notes == 1


def test_C169_rhythm_hours_and_daily_limit(mail_db: Engine) -> None:
    ready(mail_db)
    _queue(mail_db, "a@martin.fr", "b@martin.fr", "c@martin.fr")
    assert _run(mail_db, TUESDAY.replace(hour=20)) == (False, 0)  # 21 h à Paris
    assert _run(mail_db)[0]
    assert _run(mail_db, TUESDAY + timedelta(seconds=30)) == (False, 0)  # trop tôt
    assert _run(mail_db, TUESDAY + timedelta(seconds=121))[0]
    with mail_db.begin() as conn:
        save_daily_limit(conn, 2)
    assert _run(mail_db, TUESDAY + timedelta(seconds=300)) == (False, 0)  # plafond atteint
    assert _run(mail_db, TUESDAY + timedelta(days=1))[0]  # le lendemain


def test_C170_rechecked_at_send_time(mail_db: Engine) -> None:
    ready(mail_db)
    (pid,) = _queue(mail_db, "a@martin.fr")
    from tests.application.test_mail_batch import _opt_out

    _opt_out(mail_db, "a@martin.fr")
    assert _run(mail_db) == (True, 0)
    assert _statuses(mail_db) == [("ecarte", "désinscrit")]
    with mail_db.connect() as conn:
        assert pending_ids(conn) == []
    assert pid


def test_C170_three_gmail_refusals_stop_the_queue(mail_db: Engine) -> None:
    ready(mail_db)
    _queue(mail_db, "a@martin.fr", "b@martin.fr", "c@martin.fr", "d@martin.fr")
    for i in range(3):
        assert _run(mail_db, TUESDAY + timedelta(minutes=3 * i), status=400)[0]
    assert [s for s, _ in _statuses(mail_db)][:3] == ["echec"] * 3
    with mail_db.connect() as conn:
        assert paused(conn) is not None
    assert _run(mail_db, TUESDAY + timedelta(minutes=10)) == (False, 0)
    with mail_db.begin() as conn:
        set_paused(conn, None)  # « Reprendre »
    assert _run(mail_db, TUESDAY + timedelta(minutes=12)) == (True, 1)
