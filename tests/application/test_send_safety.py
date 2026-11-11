"""Relecture du groupe C168 à C181 : aucun mail en trop, à tort ou mal ciblé."""

import random
from datetime import datetime

import httpx
from sqlalchemy import Engine, text

from prospection.application.mail_batch import batch_preview, queue_batch
from prospection.application.mail_queue_run import send_next
from prospection.storage.mail_queue_settings import paused
from tests.application.campaign_helpers import BOX
from tests.application.mail_helpers import BASE, OAUTH, add_audited
from tests.application.test_sms_batch import sms_ready
from tests.application.test_sms_queue_run import TUESDAY, TZ, services
from tests.fake_http import fake_client

RNG = random.Random(0)  # noqa: S311 (attente tirée, rejouable)


def _mail(engine: Engine, client: httpx.Client, now: datetime = TUESDAY) -> bool:
    return send_next(engine, BOX, client, OAUTH, BASE, now, TZ, RNG)


def _one(engine: Engine, email: str = "a@martin.fr") -> int:
    pid = add_audited(engine, contacts_email=email)
    queue_batch(engine, BOX, [pid], TUESDAY)
    return pid


def test_C170_gmail_setup_error_stops_the_queue_without_blaming_the_address(
    mail_db: Engine,
) -> None:
    sms_ready(mail_db)
    _one(mail_db)

    def bad_client(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(401, json={"error": "invalid_client"})
        return httpx.Response(200, json={"id": "m1", "threadId": "fil-1"})

    client, _ = fake_client(bad_client)
    _mail(mail_db, client)
    with mail_db.connect() as conn:
        assert paused(conn) is not None
        assert conn.execute(text("SELECT status FROM mail_queue")).scalar_one() == "attente"


def test_C173_reports_from_before_the_check_are_to_be_checked(mail_db: Engine) -> None:
    from prospection.storage.site_codec import decode_site, encode_site
    from tests.application.mail_helpers import SITE

    data = encode_site(SITE)
    del data["unconfirmed"]
    old = decode_site(data)
    assert old is not None and old.unconfirmed


def test_C174_shared_domain_checked_again_when_queuing(mail_db: Engine) -> None:
    sms_ready(mail_db)
    ids = [add_audited(mail_db, contacts_email=f"{n}@martin.fr") for n in "abc"]
    with mail_db.begin() as conn:
        for i, pid in enumerate(ids):
            conn.execute(text(
                "UPDATE prospects SET data_json = jsonb_set(jsonb_set(data_json, '{website}', "
                "'\"http://martin.fr/\"'), '{name}', to_jsonb(CAST(:n AS text))) WHERE id = :p"
            ), {"n": f"Entreprise {i}", "p": pid})  # fmt: skip
    rows = batch_preview(mail_db, BOX, ids).rows
    assert {r.reason for r in rows} == {"site d'une plateforme (partagé)"}


def test_C169_unexpected_error_closes_the_line_instead_of_looping(
    mail_db: Engine, monkeypatch: object
) -> None:
    import pytest

    import prospection.application.mail_queue_run as run

    sms_ready(mail_db)
    _one(mail_db)

    def broken(*args: object) -> object:
        raise ValueError("donnée illisible")

    assert isinstance(monkeypatch, pytest.MonkeyPatch)
    monkeypatch.setattr(run, "load_context", broken)
    client, _ = services()
    assert _mail(mail_db, client)
    with mail_db.connect() as conn:
        assert conn.execute(text("SELECT status FROM mail_queue")).scalar_one() == "echec"


def test_C169_one_sender_at_a_time(mail_db: Engine) -> None:
    from prospection.storage.send_lock import MAIL_LOCK as LOCK_ID

    sms_ready(mail_db)
    _one(mail_db)
    client, recorder = services()
    with mail_db.connect() as other:
        other.execute(text("SELECT pg_advisory_lock(:k)"), {"k": LOCK_ID})
        assert not _mail(mail_db, client)
        other.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_ID})
    assert recorder.requests == []
