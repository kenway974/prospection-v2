"""Envoi d'une notification au service de push du navigateur (protocole Web Push, VAPID).
Contenu chiffré de bout en bout (aes128gcm, bibliothèque pywebpush) : le service de push
ne lit pas le texte. Seules les adresses des services connus sont appelées."""

import base64
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid
from pywebpush import WebPusher

from prospection.domain.push_rules import allowed_endpoint

TIMEOUT = 10.0
TTL_SECONDS = 24 * 3600  # téléphone éteint : la notification attend un jour au plus


class PushGone(Exception):
    """Abonnement expiré ou retiré (404, 410) : à oublier."""


class PushFailed(Exception):
    """Service injoignable ou refus passager : nouvel essai plus tard."""


@dataclass(frozen=True)
class VapidKeys:
    private_key: str  # brute, base64url (variable VAPID_PRIVATE_KEY)
    public_key: str  # point non compressé, base64url (donné au navigateur)
    subject: str  # mailto:… ou https://… : qui contacter en cas d'abus


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate_vapid_keys() -> tuple[str, str]:
    """(clé privée, clé publique), en base64url."""
    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_numbers().private_value.to_bytes(32, "big")
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return _b64(private), _b64(public)


def send_push(
    client: httpx.Client, endpoint: str, p256dh: str, auth: str, payload: bytes,
    keys: VapidKeys, now: datetime, urgency: str = "normal",
) -> None:  # fmt: skip
    if not allowed_endpoint(endpoint):
        raise PushGone("service de notification inconnu")
    subscription = {"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}
    try:
        body = WebPusher(subscription).encode(payload, "aes128gcm")["body"]
    except Exception:  # clés du navigateur illisibles : abonnement inutilisable
        raise PushGone("clés d'abonnement illisibles") from None
    parts = urlsplit(endpoint)
    claims = {"sub": keys.subject, "aud": f"{parts.scheme}://{parts.netloc}",
              "exp": int(now.timestamp()) + 12 * 3600}  # fmt: skip
    headers = Vapid.from_raw(keys.private_key.encode()).sign(claims)
    headers |= {"Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream",
                "TTL": str(TTL_SECONDS), "Urgency": urgency}  # fmt: skip
    try:
        response = client.post(endpoint, content=body, headers=headers, timeout=TIMEOUT)
    except httpx.HTTPError as error:
        raise PushFailed(f"service injoignable ({type(error).__name__})") from None
    if response.status_code in (404, 410):
        raise PushGone(f"abonnement expiré ({response.status_code})")
    if not 200 <= response.status_code < 300:
        raise PushFailed(f"service de notification : réponse {response.status_code}")
