"""Relecture du groupe C168 à C181 : aucun mail en trop, à tort ou mal ciblé."""

import random
from datetime import datetime, timedelta

import httpx
from sqlalchemy import Engine, text

from prospection.application.mail_batch import batch_preview, queue_batch
from prospection.application.mail_bounce import mark_bounced
from prospection.application.mail_queue_run import send_next
from prospection.application.sms_queue_run import send_next_sms
from tests.application.campaign_helpers import BOX
from tests.application.mail_helpers import BASE, OAUTH, add_audited
from tests.application.test_mail_batch import _opt_out
from tests.application.test_sms_batch import sms_ready
from tests.application.test_sms_queue_run import TUESDAY, TZ, services, sms_texts
from tests.fake_http import fake_client

RNG = random.Random(0)  # noqa: S311 (attente tirée, rejouable)


def _mail(engine: Engine, client: httpx.Client, now: datetime = TUESDAY) -> bool:
    return send_next(engine, BOX, client, OAUTH, BASE, now, TZ, RNG)


def _one(engine: Engine, email: str = "a@martin.fr") -> int:
    pid = add_audited(engine, contacts_email=email)
    queue_batch(engine, BOX, [pid], TUESDAY)
    return pid


def test_C176_no_sms_after_unsubscribing_from_the_mail(mail_db: Engine) -> None:
    sms_ready(mail_db)
    _one(mail_db)
    client, recorder = services()
    assert _mail(mail_db, client)
    _opt_out(mail_db, "a@martin.fr")
    send_next_sms(mail_db, BOX, client, OAUTH, TUESDAY + timedelta(minutes=21), TZ)
    assert sms_texts(recorder) == []


def test_C177_lost_brevo_answer_is_never_sent_again(mail_db: Engine) -> None:
    sms_ready(mail_db)
    _one(mail_db)
    client, _ = services()
    _mail(mail_db, client)
    posts: list[int] = []

    def timeout(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.brevo.com":
            posts.append(1)
            raise httpx.ReadTimeout("réponse perdue", request=request)
        return httpx.Response(200, json={"messages": []})

    lost, _ = fake_client(timeout)
    later = TUESDAY + timedelta(minutes=21)
    send_next_sms(mail_db, BOX, lost, OAUTH, later, TZ)
    send_next_sms(mail_db, BOX, lost, OAUTH, later + timedelta(hours=1), TZ)
    assert len(posts) == 1


def test_C176_sms_only_when_the_registry_says_publishable(mail_db: Engine) -> None:
    sms_ready(mail_db)
    pid = add_audited(mail_db, contacts_email="a@martin.fr")
    with mail_db.begin() as conn:
        conn.execute(text("UPDATE prospects SET registry_status = NULL WHERE id = :p"), {"p": pid})
    assert batch_preview(mail_db, BOX, [pid]).rows[0].sms_reason == "registre non vérifié"


def test_C177_retry_after_brevo_down_still_reads_a_late_bounce(mail_db: Engine) -> None:
    sms_ready(mail_db)
    pid = _one(mail_db)
    client, _ = services()
    _mail(mail_db, client)
    down, _ = services(brevo=429)
    later = TUESDAY + timedelta(minutes=21)
    send_next_sms(mail_db, BOX, down, OAUTH, later, TZ)
    mark_bounced(mail_db, pid, later + timedelta(minutes=5), BOX.pepper)
    up, recorder = services()
    send_next_sms(mail_db, BOX, up, OAUTH, later + timedelta(minutes=31), TZ)
    assert "ne vous parvient pas" in sms_texts(recorder)[0]


def test_C177_sms_spaced_and_wording_fits_the_case(mail_db: Engine) -> None:
    sms_ready(mail_db)
    long_name = "Société Générale des Travaux Paysagers de l'Hérault"
    ids = []
    for n in "ab":
        pid = add_audited(mail_db)
        with mail_db.begin() as conn:
            conn.execute(text("UPDATE prospects SET site_json = jsonb_set(site_json, "
                              "'{contacts,emails}', '[]'), data_json = jsonb_set(data_json, "
                              "'{name}', to_jsonb(CAST(:n AS text))) WHERE id = :p"),
                         {"p": pid, "n": long_name + n})  # fmt: skip
        ids.append(pid)
    queue_batch(mail_db, BOX, ids, TUESDAY)
    client, recorder = services()
    assert send_next_sms(mail_db, BOX, client, OAUTH, TUESDAY, TZ)
    assert not send_next_sms(mail_db, BOX, client, OAUTH, TUESDAY + timedelta(seconds=20), TZ)
    sent = sms_texts(recorder)[0]
    assert sent.startswith("Bonjour, ") or long_name in sent  # jamais un nom coupé
