"""Gmail : connexion OAuth Google et envoi par l'API Gmail en HTTPS (C144, C146).

Droits demandés : envoyer des mails (gmail.send), connaître l'adresse du compte (openid
email) et voir les en-têtes d'une conversation (gmail.metadata : qui a répondu au mail d'audit) ;
l'app ne lit jamais le contenu d'un mail. L'envoi SMTP est bloqué sur Railway (hors
offre Pro) : l'API HTTPS le remplace. Réponses validées ; aucun jeton dans les journaux.
"""

import base64
import json
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.key_check import KeyCheck
from prospection.http_client import json_object, send

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 (adresse, pas un secret)
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
# Envoyer ; connaître l'adresse du compte ; voir les en-têtes d'une conversation (réponses, C163)
SCOPES = ("openid email https://www.googleapis.com/auth/gmail.send "
          "https://www.googleapis.com/auth/gmail.metadata")  # fmt: skip
LABEL = "Gmail"


class GmailUnavailable(Exception):
    """Google ne répond pas ou demande de ralentir : réessayer dans un instant."""


class GmailRevoked(Exception):
    """La connexion Gmail a expiré ou a été retirée : la refaire dans Réglages."""


class GmailUncertain(Exception):
    """Réponse de Gmail perdue pendant l'envoi : le mail est peut-être parti."""


class GmailRefused(Exception):
    """Google refuse la demande (message invalide, connexion incomplète)."""


@dataclass(frozen=True)
class GmailOAuth:
    client_id: str
    client_secret: str


@dataclass(frozen=True)
class GmailGrant:
    refresh_token: str
    address: str


class _Grant(BaseModel):
    refresh_token: str
    id_token: str


class _Identity(BaseModel):
    email: str
    email_verified: bool


def authorize_url(oauth: GmailOAuth, redirect_uri: str, state: str) -> str:
    query = {
        "client_id": oauth.client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state,
    }  # fmt: skip
    return f"{AUTH_URL}?{urlencode(query)}"


def _token(client: httpx.Client, oauth: GmailOAuth, fields: dict[str, str]) -> dict[str, object]:
    data = {"client_id": oauth.client_id, "client_secret": oauth.client_secret, **fields}
    response = send(client, "POST", TOKEN_URL, LABEL, data=data)
    if isinstance(response, KeyCheck) or response.status_code == 429 or response.status_code >= 500:
        raise GmailUnavailable
    body = json_object(response) or {}
    if response.status_code != 200:
        raise GmailRevoked if body.get("error") == "invalid_grant" else GmailRefused
    return body


def _identity(id_token: str) -> str:
    """Adresse du compte, lue dans le jeton d'identité reçu directement de Google (HTTPS)."""
    try:
        payload = id_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        identity = _Identity.model_validate(claims)
    except (IndexError, ValueError, ValidationError):
        raise GmailRefused from None
    if not identity.email_verified:
        raise GmailRefused
    return identity.email.strip().lower()


def exchange_code(
    client: httpx.Client, oauth: GmailOAuth, code: str, redirect_uri: str
) -> GmailGrant:
    body = _token(client, oauth, {"grant_type": "authorization_code", "code": code,
                                  "redirect_uri": redirect_uri})  # fmt: skip
    try:
        grant = _Grant.model_validate(body)
    except ValidationError:
        raise GmailRefused from None
    return GmailGrant(grant.refresh_token, _identity(grant.id_token))


def access_token(client: httpx.Client, oauth: GmailOAuth, refresh_token: str) -> str:
    body = _token(client, oauth, {"grant_type": "refresh_token", "refresh_token": refresh_token})
    token = body.get("access_token")
    if not isinstance(token, str) or not token:
        raise GmailRefused
    return token


def send_raw(client: httpx.Client, token: str, raw: bytes) -> str | None:
    """Envoie ; rend l'identifiant de la conversation Gmail (None si absent)."""
    encoded = base64.urlsafe_b64encode(raw).decode()
    headers = {"Authorization": f"Bearer {token}"}
    response = send(client, "POST", SEND_URL, LABEL, headers=headers, json={"raw": encoded})
    if isinstance(response, KeyCheck):
        raise GmailUncertain
    if response.status_code == 429 or response.status_code >= 500:
        raise GmailUnavailable
    if response.status_code in (401, 403):
        raise GmailRevoked
    if response.status_code != 200:
        raise GmailRefused
    thread = (json_object(response) or {}).get("threadId")
    return thread[:100] if isinstance(thread, str) and thread else None


def revoke(client: httpx.Client, refresh_token: str) -> bool:
    """Retire l'accès chez Google ; vrai si c'est fait (ou déjà fait)."""
    response = send(client, "POST", REVOKE_URL, LABEL, data={"token": refresh_token})
    if isinstance(response, KeyCheck):
        return False
    if response.status_code == 200:
        return True
    return (
        response.status_code == 400
        and (json_object(response) or {}).get("error") == "invalid_token"
    )
