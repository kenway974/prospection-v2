"""C175, C180, C181 : Brevo, avec un faux (aucun réseau) : clé, envoi d'un SMS, numéros STOP."""

import json

import httpx
import pytest

from prospection.sources.brevo import (
    BrevoNoCredits,
    BrevoRefused,
    BrevoUnavailable,
    check_brevo_key,
    send_sms,
    stop_numbers,
)
from tests.fake_http import fake_client


def test_C181_key_checked_without_sending_anything() -> None:
    client, recorder = fake_client(lambda r: httpx.Response(200, json={"email": "k@x.fr"}))
    assert check_brevo_key(client, "cle").ok
    assert recorder.requests[0].method == "GET" and recorder.requests[0].headers["api-key"] == "cle"
    refused, _ = fake_client(lambda r: httpx.Response(401, json={"code": "unauthorized"}))
    assert not check_brevo_key(refused, "cle").ok


def test_C177_marketing_sms_sent_with_sender_and_number() -> None:
    client, recorder = fake_client(lambda r: httpx.Response(201, json={"messageId": 1511882900}))
    send_sms(client, "cle", "Kenny", "+33681787325", "Bonjour")
    body = json.loads(recorder.requests[0].content)
    assert recorder.requests[0].url.path == "/v3/transactionalSMS/sms"
    assert body == {"type": "marketing", "sender": "Kenny", "recipient": "33681787325",
                    "content": "Bonjour", "tag": "audit", "unicodeEnabled": False}  # fmt: skip


@pytest.mark.parametrize(
    ("status", "error"),
    [(402, BrevoNoCredits), (400, BrevoRefused), (401, BrevoRefused), (503, BrevoUnavailable)],
)
def test_C177_failures_are_told_apart(status: int, error: type[Exception]) -> None:
    client, _ = fake_client(lambda r: httpx.Response(status, json={"code": "x"}))
    with pytest.raises(error):
        send_sms(client, "cle", "Kenny", "+33681787325", "Bonjour")


def test_C180_numbers_that_answered_stop() -> None:
    events = {"events": [{"phoneNumber": "33681787325", "event": "unsubscription"},
                         {"phoneNumber": "", "event": "unsubscription"}, {"x": 1}]}  # fmt: skip
    client, recorder = fake_client(lambda r: httpx.Response(200, json=events))
    assert stop_numbers(client, "cle") == ["+33681787325"]
    assert recorder.requests[0].url.params["event"] == "unsubscription"
    broken, _ = fake_client(lambda r: httpx.Response(200, text="<html>"))
    with pytest.raises(BrevoUnavailable):
        stop_numbers(broken, "cle")
