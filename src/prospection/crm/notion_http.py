"""Appel à l'API Notion : rythme partagé (C75) et erreurs typées (C73, C74).

Messages 401 / 403 / 404 repris de prospection-bot (services/crm/notion.py, version 530ba12) :
ils disent quoi faire.
"""

import threading
import time
from typing import Any

import httpx

from prospection.crm.notion import API_URL, LABEL, headers
from prospection.domain.key_check import KeyCheck
from prospection.http_client import json_object, send

MIN_INTERVAL = 0.34  # Notion : 3 requêtes par seconde en moyenne (C75)


class Pacer:
    """Espace toutes les requêtes Notion du processus, quel que soit le fil."""

    def __init__(self, interval: float) -> None:
        self.interval, self._next, self._lock = interval, 0.0, threading.Lock()

    def wait(self) -> None:
        with self._lock:
            delay = self._next - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self._next = time.monotonic() + self.interval


PACER = Pacer(MIN_INTERVAL)
REFUSED = {
    401: "Jeton refusé par Notion : vérifiez le « secret » de l'intégration (Réglages).",
    403: "Notion refuse l'accès : partagez la base avec l'intégration (base → ⋯ → Connexions).",
    404: "Base introuvable : partagez-la avec l'intégration (base → ⋯ → Connexions), ou "
    "choisissez-la de nouveau dans Réglages → CRM.",
}


class NotionBusy(Exception):
    """Notion trop sollicité ou muet : réessayer plus tard (après `retry_after` s si donné)."""

    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__("Notion indisponible pour l'instant : nouvel essai plus tard.")
        self.retry_after = retry_after


class NotionRefused(Exception):
    """Notion refuse la demande ; le message dit pourquoi. `general` : la clé ou la base sont
    en cause (401, 403, 404), pas ce prospect : on garde la file, on s'arrête."""

    def __init__(self, message: str, general: bool = False) -> None:
        super().__init__(message)
        self.general = general


def call(client: httpx.Client, method: str, path: str, token: str, body: Any) -> dict[str, Any]:
    PACER.wait()
    response = send(client, method, f"{API_URL}{path}", LABEL, headers=headers(token), json=body)
    if isinstance(response, KeyCheck) or response.status_code >= 500:
        raise NotionBusy
    if response.status_code == 429:
        try:
            raise NotionBusy(float(response.headers.get("Retry-After", "")))
        except ValueError:
            raise NotionBusy from None
    data = json_object(response)
    if response.status_code != 200 or data is None:
        detail = str((data or {}).get("message", ""))[:300]
        general = response.status_code in REFUSED
        raise NotionRefused(
            REFUSED.get(response.status_code) or f"Notion refuse : {detail}", general
        )
    return data
