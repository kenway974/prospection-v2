"""Conversations Gmail du mail d'audit : en-têtes « From » seulement, jamais le contenu (C163)."""

import httpx

from prospection.domain.key_check import KeyCheck
from prospection.http_client import json_object, send
from prospection.sources.gmail import LABEL, GmailRevoked, GmailUnavailable

THREAD_URL = "https://gmail.googleapis.com/gmail/v1/users/me/threads/"


class GmailScopeMissing(Exception):
    """Gmail n'a pas encore le droit de voir les en-têtes : relier Gmail à nouveau."""


def thread_senders(client: httpx.Client, token: str, thread_id: str) -> list[str]:
    """En-tête « From » de chaque message de la conversation, dans l'ordre ; jamais le
    contenu (C163). Conversation supprimée : liste vide."""
    response = send(client, "GET", THREAD_URL + thread_id, LABEL,
                    headers={"Authorization": f"Bearer {token}"},
                    params={"format": "metadata", "metadataHeaders": "From"})  # fmt: skip
    if isinstance(response, KeyCheck) or response.status_code == 429 or response.status_code >= 500:
        raise GmailUnavailable
    if response.status_code == 404:
        return []
    if response.status_code == 403 and "SCOPE_INSUFFICIENT" in response.text.upper():
        raise GmailScopeMissing
    if response.status_code in (401, 403):
        raise GmailRevoked
    messages = (json_object(response) or {}).get("messages")
    senders = []
    for message in messages if isinstance(messages, list) else []:
        headers = (message.get("payload") or {}).get("headers") if isinstance(message, dict) else []
        for header in headers if isinstance(headers, list) else []:
            if isinstance(header, dict) and str(header.get("name", "")).lower() == "from":
                senders.append(str(header.get("value", ""))[:300])
    return senders
