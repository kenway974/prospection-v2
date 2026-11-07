"""C144, C146 : connexion OAuth à Gmail et envoi par l'API Gmail (faux Google, aucun réseau)."""

import base64
import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from prospection.sources.gmail import (
    GmailOAuth,
    GmailRefused,
    GmailRevoked,
    GmailUnavailable,
    access_token,
    authorize_url,
    exchange_code,
    send_raw,
)
from tests.fake_http import fake_client, json_reply, timeout

OAUTH = GmailOAuth("id-client", "secret-client")
REDIRECT = "https://app.fr/reglages/gmail/retour"


def id_token(email: str, verified: bool = True) -> str:
    payload = (
        base64.urlsafe_b64encode(json.dumps({"email": email, "email_verified": verified}).encode())
        .decode()
        .rstrip("=")
    )
    return f"entete.{payload}.signature"


def test_C144_consent_page_asks_only_to_send_mails() -> None:
    url = authorize_url(OAUTH, REDIRECT, "etat-123")
    query = parse_qs(urlsplit(url).query)
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert query["scope"] == [
        "openid email https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/gmail.metadata"
    ]
    assert query["state"] == ["etat-123"] and query["access_type"] == ["offline"]
    assert query["redirect_uri"] == [REDIRECT] and query["client_id"] == ["id-client"]


def test_C144_code_exchanged_for_a_lasting_token_and_the_address() -> None:
    reply = {"refresh_token": "jeton-long", "id_token": id_token("Kapignolet18@gmail.com")}
    client, recorder = fake_client(json_reply(200, reply))
    grant = exchange_code(client, OAUTH, "code-1", REDIRECT)
    assert (grant.refresh_token, grant.address) == ("jeton-long", "kapignolet18@gmail.com")
    sent = parse_qs(recorder.requests[0].content.decode())
    assert sent["grant_type"] == ["authorization_code"] and sent["code"] == ["code-1"]


def test_C144_exchange_without_lasting_token_or_verified_address_is_refused() -> None:
    for reply in ({"id_token": id_token("a@gmail.com")},
                  {"refresh_token": "j", "id_token": id_token("a@gmail.com", False)},
                  {"refresh_token": "j", "id_token": "illisible"}):  # fmt: skip
        client, _ = fake_client(json_reply(200, reply))
        with pytest.raises(GmailRefused):
            exchange_code(client, OAUTH, "code", REDIRECT)


def test_C146_access_token_and_revoked_connection() -> None:
    client, _ = fake_client(json_reply(200, {"access_token": "court", "expires_in": 3599}))
    assert access_token(client, OAUTH, "jeton-long") == "court"
    client, _ = fake_client(json_reply(400, {"error": "invalid_grant"}))
    with pytest.raises(GmailRevoked):
        access_token(client, OAUTH, "jeton-long")
    client, _ = fake_client(timeout)
    with pytest.raises(GmailUnavailable):
        access_token(client, OAUTH, "jeton-long")


def test_C146_message_sent_as_base64url() -> None:
    client, recorder = fake_client(json_reply(200, {"id": "m1"}))
    send_raw(client, "court", b"Subject: x\r\n\r\ncorps")
    request = recorder.requests[0]
    assert request.headers["Authorization"] == "Bearer court"
    raw = json.loads(request.content)["raw"]
    assert base64.urlsafe_b64decode(raw + "==") == b"Subject: x\r\n\r\ncorps"


@pytest.mark.parametrize(("status", "error"), [(401, GmailRevoked), (403, GmailRevoked),
                                               (400, GmailRefused), (429, GmailUnavailable),
                                               (503, GmailUnavailable)])  # fmt: skip
def test_C146_send_failures_said_plainly(status: int, error: type[Exception]) -> None:
    client, _ = fake_client(lambda r: httpx.Response(status, json={"error": {"message": "x"}}))
    with pytest.raises(error):
        send_raw(client, "court", b"x")


def test_C144_access_withdrawn_at_google() -> None:
    from prospection.sources.gmail import revoke

    client, recorder = fake_client(json_reply(200, {}))
    assert revoke(client, "jeton-long") is True
    request = recorder.requests[0]
    assert str(request.url) == "https://oauth2.googleapis.com/revoke"
    assert parse_qs(request.content.decode())["token"] == ["jeton-long"]
    client, _ = fake_client(json_reply(400, {"error": "invalid_token"}))
    assert revoke(client, "jeton-long") is True  # déjà retiré chez Google
    client, _ = fake_client(timeout)
    assert revoke(client, "jeton-long") is False


def test_C163_thread_senders_from_headers_only() -> None:
    from prospection.sources.gmail_threads import GmailScopeMissing, thread_senders

    thread = {"messages": [
        {"payload": {"headers": [{"name": "From", "value": "Kenny <kapignolet18@gmail.com>"}]}},
        {"payload": {"headers": [{"name": "From", "value": "Martin <contact@martin.fr>"}]}},
    ]}  # fmt: skip
    client, recorder = fake_client(json_reply(200, thread))
    assert thread_senders(client, "court", "fil-1") == [
        "Kenny <kapignolet18@gmail.com>", "Martin <contact@martin.fr>",
    ]  # fmt: skip
    request = recorder.requests[0]
    assert request.url.path == "/gmail/v1/users/me/threads/fil-1"
    assert request.url.params["format"] == "metadata"
    assert request.url.params.get_list("metadataHeaders") == ["From"]
    client, _ = fake_client(json_reply(404, {}))
    assert thread_senders(client, "court", "fil-1") == []
    scope = {"error": {"code": 403, "status": "PERMISSION_DENIED",
                       "details": [{"reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}]}}  # fmt: skip
    client, _ = fake_client(json_reply(403, scope))
    with pytest.raises(GmailScopeMissing):
        thread_senders(client, "court", "fil-1")
