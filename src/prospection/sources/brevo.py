"""Brevo : envoi des SMS du mail d'audit et numéros qui ont répondu STOP (C175 à C181).

API officielle, clé dans l'en-tête `api-key`. Les SMS partent en type « marketing » : Brevo
ajoute lui-même la mention STOP et bloque les numéros qui l'ont envoyée. Chaque réponse est
validée ; une panne, un refus ou des crédits épuisés sont distingués.
"""

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.key_check import KeyCheck, unexpected
from prospection.domain.services import Service
from prospection.http_client import json_object, send

API = "https://api.brevo.com/v3"
LABEL = Service.BREVO.label
TAG = "audit"


class BrevoUnavailable(Exception):
    """Brevo ne répond pas ou répond de façon inattendue : réessayer plus tard."""


class BrevoRefused(Exception):
    """Brevo refuse (clé, expéditeur ou numéro) : ce SMS ne partira pas tel quel."""


class BrevoNoCredits(Exception):
    """Plus de crédits SMS chez Brevo : à racheter sur app.brevo.com."""


class _Event(BaseModel):
    phoneNumber: str = ""


class _Events(BaseModel):
    events: list[_Event] = []


def _headers(key: str) -> dict[str, str]:
    return {"api-key": key, "Accept": "application/json"}


def check_brevo_key(client: httpx.Client, key: str) -> KeyCheck:
    """Test gratuit : lecture du compte, aucun SMS envoyé."""
    response = send(client, "GET", f"{API}/account", LABEL, headers=_headers(key))
    if isinstance(response, KeyCheck):
        return response
    if response.status_code in (401, 403):
        return KeyCheck(False, "Clé refusée par Brevo : vérifiez-la sur app.brevo.com.")
    if response.status_code == 200 and json_object(response) is not None:
        return KeyCheck(True, "Clé Brevo valide.")
    return unexpected(LABEL)


def send_sms(client: httpx.Client, key: str, sender: str, mobile: str, text: str) -> None:
    """`mobile` au format international (+336…)."""
    body = {"type": "marketing", "sender": sender, "recipient": mobile.removeprefix("+"),
            "content": text, "tag": TAG, "unicodeEnabled": False}  # fmt: skip
    url = f"{API}/transactionalSMS/sms"
    response = send(client, "POST", url, LABEL, headers=_headers(key), json=body)
    if isinstance(response, KeyCheck) or response.status_code == 429:
        raise BrevoUnavailable
    if response.status_code == 402:
        raise BrevoNoCredits
    if response.status_code in (400, 401, 403, 404):
        raise BrevoRefused
    if response.status_code not in (200, 201) or json_object(response) is None:
        raise BrevoUnavailable


def stop_numbers(client: httpx.Client, key: str, days: int = 2) -> list[str]:
    """Numéros (+33…) qui ont répondu STOP ces derniers jours."""
    params = {"event": "unsubscription", "days": days, "limit": 2500}
    url = f"{API}/transactionalSMS/statistics/events"
    response = send(client, "GET", url, LABEL, headers=_headers(key), params=params)
    if isinstance(response, KeyCheck) or response.status_code != 200:
        raise BrevoUnavailable
    body = json_object(response)
    if body is None:
        raise BrevoUnavailable
    try:
        events = _Events.model_validate(body).events
    except ValidationError:
        raise BrevoUnavailable from None
    return [f"+{e.phoneNumber.lstrip('+')}" for e in events if e.phoneNumber.strip()]
