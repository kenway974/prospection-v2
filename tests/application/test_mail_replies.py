"""C163 : réponses (et refus du serveur) repérées dans la conversation Gmail, sans lire le
contenu ; Gmail à relier à nouveau si le droit manque."""

from collections.abc import Callable
from datetime import timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.mail_replies import check_replies
from prospection.application.prospect_card import card
from prospection.storage.mail_send_log import all_sends
from prospection.storage.mail_settings import replies_blocked
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import OAUTH, add_audited, ready
from tests.application.test_audit_mail import PARIS, send
from tests.fake_http import fake_client

ME = "Kenny <kapignolet18@gmail.com>"


def gmail(senders: list[str], status: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "court"})
        if status != 200:
            details = [{"reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}]
            return httpx.Response(status, json={"error": {"details": details}})
        messages = [{"payload": {"headers": [{"name": "From", "value": s}]}} for s in senders]
        return httpx.Response(200, json={"messages": messages})

    return answer


def run(engine: Engine, handler: Callable[[httpx.Request], httpx.Response], hours: int = 0) -> int:
    client, _ = fake_client(handler)
    return check_replies(engine, BOX, client, OAUTH, NOW + timedelta(hours=hours))


def sent_one(engine: Engine) -> int:
    pid = add_audited(engine)
    ready(engine)
    send(engine, pid)
    return pid


def test_C163_reply_found_and_noted(mail_db: Engine) -> None:
    pid = sent_one(mail_db)
    assert run(mail_db, gmail([ME])) == 1  # pas encore de réponse
    assert run(mail_db, gmail([ME, "Martin <contact@martin.fr>"])) == 0  # revu dans 6 h
    assert run(mail_db, gmail([ME, "Martin <contact@martin.fr>"]), hours=7) == 1
    with mail_db.connect() as conn:
        assert all_sends(conn)[0].replied
    assert card(mail_db, pid, NOW, PARIS).notes[0].text.startswith("Réponse reçue au mail d'audit")


def test_C163_server_refusal_marks_the_mail_refused(mail_db: Engine) -> None:
    pid = sent_one(mail_db)
    failure = {"From": DAEMON, "Subject": "Delivery Status Notification (Failure)"}
    run(mail_db, headers_gmail([{"From": ME}, failure]))
    shown = card(mail_db, pid, NOW, PARIS)
    assert shown.mail_sent_on is None and "refusé par le serveur" in shown.notes[0].text


def test_C163_missing_right_asks_to_reconnect_gmail(mail_db: Engine) -> None:
    sent_one(mail_db)
    assert run(mail_db, gmail([], status=403)) == 0
    with mail_db.connect() as conn:
        assert replies_blocked(conn)
    assert run(mail_db, gmail([ME, "x@y.fr"]), hours=7) == 0  # plus d'essai avant de relier


def headers_gmail(messages: list[dict[str, str]]) -> Callable[[httpx.Request], httpx.Response]:
    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "court"})
        found = [{"payload": {"headers": [{"name": k, "value": v} for k, v in m.items()]}}
                 for m in messages]  # fmt: skip
        return httpx.Response(200, json={"messages": found})

    return answer


DAEMON = "Mail Delivery Subsystem <mailer-daemon@googlemail.com>"


def test_C163_delay_notice_is_not_a_refusal(mail_db: Engine) -> None:
    pid = sent_one(mail_db)
    delay = {"From": DAEMON, "Subject": "Delivery Status Notification (Delay)"}
    run(mail_db, headers_gmail([{"From": ME}, delay]))
    assert card(mail_db, pid, NOW, PARIS).mail_sent_on is not None  # toujours en cours


def test_C163_auto_reply_and_lookalike_address_handled(mail_db: Engine) -> None:
    sent_one(mail_db)
    away = {"From": "Martin <contact@martin.fr>", "Subject": "Réponse automatique : absent",
            "Auto-Submitted": "auto-replied"}  # fmt: skip
    lookalike = {"From": "X <xkapignolet18@gmail.com>", "Subject": "Re: votre site"}
    run(mail_db, headers_gmail([{"From": ME}, away]))
    with mail_db.connect() as conn:
        assert not all_sends(conn)[0].replied  # réponse automatique : pas une conversation
    run(mail_db, headers_gmail([{"From": ME}, lookalike]), hours=7)
    with mail_db.connect() as conn:
        assert all_sends(conn)[0].replied  # une autre adresse, même si elle contient la mienne
