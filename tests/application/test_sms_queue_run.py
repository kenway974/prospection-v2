"""C177, C178, C180 : la tâche de fond envoie le SMS 20 minutes après le mail, dans la bonne
version ; un refus tardif déclenche un second SMS ; les STOP de Brevo sont repris."""

import json
import random
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.mail_batch import batch_preview, queue_batch
from prospection.application.mail_bounce import mark_bounced
from prospection.application.mail_queue_run import send_next
from prospection.application.sms_queue_run import send_next_sms, sync_stops
from tests.application.campaign_helpers import BOX
from tests.application.mail_helpers import BASE, OAUTH, add_audited
from tests.application.test_sms_batch import MOBILE, sms_ready
from tests.fake_http import Recorder, fake_client

TUESDAY = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)  # 10 h à Paris
TZ = "Europe/Paris"
BOUNCE = {"from": "Mail Delivery Subsystem <mailer-daemon@googlemail.com>",
          "subject": "Delivery Status Notification (Failure)"}  # fmt: skip


def services(bounced: bool = False, brevo: int = 201, stops: tuple[str, ...] = ()
             ) -> tuple[httpx.Client, Recorder]:  # fmt: skip
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "court"})
        if request.url.host == "api.brevo.com":
            if "events" in request.url.path:
                events = [{"phoneNumber": n.lstrip("+"), "event": "unsubscription"} for n in stops]
                return httpx.Response(200, json={"events": events})
            return httpx.Response(brevo, json={"messageId": 1})
        if request.method == "GET":  # conversation Gmail : en-têtes seulement
            names = (("From", BOUNCE["from"]), ("Subject", BOUNCE["subject"]))
            headers = [{"name": n, "value": v} for n, v in names] if bounced else []
            return httpx.Response(200, json={"messages": [{"payload": {"headers": headers}}]})
        return httpx.Response(200, json={"id": "m1", "threadId": "fil-1"})

    return fake_client(handler)


def sms_texts(recorder: Recorder) -> list[str]:
    return [json.loads(r.content)["content"] for r in recorder.requests
            if r.url.host == "api.brevo.com" and r.method == "POST"]  # fmt: skip


def _mail_then_sms(engine: Engine, bounced: bool = False) -> tuple[list[str], Recorder]:
    client, recorder = services(bounced)
    assert send_next(engine, BOX, client, OAUTH, BASE, TUESDAY, TZ, random.Random(0))  # noqa: S311
    assert not send_next_sms(engine, BOX, client, OAUTH, TUESDAY + timedelta(minutes=5), TZ)
    assert send_next_sms(engine, BOX, client, OAUTH, TUESDAY + timedelta(minutes=21), TZ)
    return sms_texts(recorder), recorder


def test_C177_sms_20_minutes_after_the_mail_points_to_it(mail_db: Engine) -> None:
    sms_ready(mail_db)
    queue_batch(mail_db, BOX, [add_audited(mail_db, contacts_email="a@martin.fr")], TUESDAY)
    texts, recorder = _mail_then_sms(mail_db)
    assert len(texts) == 1 and "détail par mail" in texts[0] and len(texts[0]) <= 140
    sent = next(r for r in recorder.requests if r.url.host == "api.brevo.com")
    assert json.loads(sent.content)["recipient"] == MOBILE.lstrip("+")


def test_C177_bounce_found_before_the_sms_says_the_address_is_blocked(mail_db: Engine) -> None:
    sms_ready(mail_db)
    queue_batch(mail_db, BOX, [add_audited(mail_db, contacts_email="a@martin.fr")], TUESDAY)
    texts, _ = _mail_then_sms(mail_db, bounced=True)
    assert "ne vous parvient pas" in texts[0] and "06 81 78 73 25" in texts[0]


def test_C177_without_email_the_sms_leaves_at_once_and_only_in_hours(mail_db: Engine) -> None:
    sms_ready(mail_db)
    pid = add_audited(mail_db)
    with mail_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET site_json = jsonb_set(site_json, "
                             "'{contacts,emails}', '[]') WHERE id = %(p)s", {"p": pid})  # fmt: skip
    queue_batch(mail_db, BOX, [pid], TUESDAY)
    client, recorder = services()
    assert not send_next_sms(mail_db, BOX, client, OAUTH, TUESDAY.replace(hour=19), TZ)
    assert send_next_sms(mail_db, BOX, client, OAUTH, TUESDAY, TZ)
    assert "écrivez-moi" in sms_texts(recorder)[0]
    assert not send_next_sms(mail_db, BOX, client, OAUTH, TUESDAY + timedelta(hours=1), TZ)


def test_C177_brevo_down_retries_later_without_losing_the_sms(mail_db: Engine) -> None:
    sms_ready(mail_db)
    pid = add_audited(mail_db)
    with mail_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET site_json = jsonb_set(site_json, "
                             "'{contacts,emails}', '[]') WHERE id = %(p)s", {"p": pid})  # fmt: skip
    queue_batch(mail_db, BOX, [pid], TUESDAY)
    down, _ = services(brevo=503)
    assert not send_next_sms(mail_db, BOX, down, OAUTH, TUESDAY, TZ)
    up, recorder = services()
    assert not send_next_sms(mail_db, BOX, up, OAUTH, TUESDAY + timedelta(minutes=10), TZ)
    assert send_next_sms(mail_db, BOX, up, OAUTH, TUESDAY + timedelta(minutes=31), TZ)
    assert len(sms_texts(recorder)) == 1


def test_C178_late_bounce_sends_one_more_sms_once(mail_db: Engine) -> None:
    sms_ready(mail_db)
    pid = add_audited(mail_db, contacts_email="a@martin.fr")
    queue_batch(mail_db, BOX, [pid], TUESDAY)
    _mail_then_sms(mail_db)
    later = TUESDAY + timedelta(hours=2)
    mark_bounced(mail_db, pid, later, BOX.pepper)
    client, recorder = services()
    assert send_next_sms(mail_db, BOX, client, OAUTH, later, TZ)
    assert "refusé par votre messagerie" in sms_texts(recorder)[0]
    assert not send_next_sms(mail_db, BOX, client, OAUTH, later + timedelta(hours=1), TZ)


def test_C180_stop_numbers_from_brevo_are_respected(mail_db: Engine) -> None:
    sms_ready(mail_db)
    pid = add_audited(mail_db, contacts_email="a@martin.fr")
    client, recorder = services(stops=(MOBILE,))
    assert sync_stops(mail_db, BOX, client, TUESDAY)
    assert not sync_stops(mail_db, BOX, client, TUESDAY + timedelta(hours=2))  # une fois par jour
    assert batch_preview(mail_db, BOX, [pid]).rows[0].sms_reason == "a répondu STOP"
    assert len(recorder.requests) == 1


def test_C177_cancelling_the_mail_cancels_its_sms(mail_db: Engine) -> None:
    from prospection.application.mail_queue_view import cancel_line

    sms_ready(mail_db)
    queue_batch(mail_db, BOX, [add_audited(mail_db, contacts_email="a@martin.fr")], TUESDAY)
    with mail_db.connect() as conn:
        queue_id = conn.exec_driver_sql("SELECT id FROM mail_queue").scalar_one()
    cancel_line(mail_db, queue_id, TUESDAY)
    with mail_db.connect() as conn:
        assert conn.exec_driver_sql("SELECT status FROM sms_queue").scalar_one() == "annule"
