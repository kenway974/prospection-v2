"""Web Push : notification chiffrée, signée (VAPID), vers un service connu seulement."""

import base64
import os
from datetime import UTC, datetime

import http_ece
import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from prospection.sources.web_push import (
    PushFailed,
    PushGone,
    VapidKeys,
    generate_vapid_keys,
    send_push,
)
from tests.fake_http import fake_client, timeout

NOW = datetime(2026, 10, 29, 9, tzinfo=UTC)
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def phone() -> tuple[ec.EllipticCurvePrivateKey, str, str, bytes]:
    """Ce que fait le navigateur : sa paire de clés et son secret d'authentification."""
    key, secret = ec.generate_private_key(ec.SECP256R1()), os.urandom(16)
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return key, b64(public), b64(secret), secret


def keys() -> VapidKeys:
    private, public = generate_vapid_keys()
    return VapidKeys(private, public, "mailto:moi@example.fr")


def test_notification_encrypted_for_the_phone_and_signed() -> None:
    receiver, p256dh, auth, secret = phone()
    client, seen = fake_client(lambda r: httpx.Response(201))
    vapid = keys()
    send_push(client, ENDPOINT, p256dh, auth, b'{"body": "Rappeler"}', vapid, NOW)
    [sent] = seen.requests
    assert sent.headers["Content-Encoding"] == "aes128gcm" and sent.headers["TTL"] == "86400"
    assert b"Rappeler" not in sent.content  # illisible pour le service de push
    clear = http_ece.decrypt(sent.content, private_key=receiver, auth_secret=secret)
    assert clear == b'{"body": "Rappeler"}'
    token = sent.headers["Authorization"]
    assert token.startswith("vapid t=") and f"k={vapid.public_key}" in token


def test_expired_unknown_or_busy_service() -> None:
    _, p256dh, auth, _ = phone()
    gone, _ = fake_client(lambda r: httpx.Response(410))
    with pytest.raises(PushGone):
        send_push(gone, ENDPOINT, p256dh, auth, b"x", keys(), NOW)
    never, calls = fake_client(lambda r: httpx.Response(201))
    with pytest.raises(PushGone):
        send_push(never, "https://169.254.169.254/latest", p256dh, auth, b"x", keys(), NOW)
    assert calls.requests == []
    with pytest.raises(PushFailed):
        send_push(fake_client(lambda r: httpx.Response(429))[0], ENDPOINT, p256dh, auth, b"x",
                  keys(), NOW)  # fmt: skip
    with pytest.raises(PushFailed):
        send_push(fake_client(timeout)[0], ENDPOINT, p256dh, auth, b"x", keys(), NOW)
    with pytest.raises(PushGone):
        send_push(never, ENDPOINT, "pas-une-cle", auth, b"x", keys(), NOW)
