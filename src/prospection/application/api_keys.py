"""Saisie, état et lecture des clés API (C02, C04, C85)."""

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine

from prospection.domain.services import Service
from prospection.storage.api_keys import delete_key, load_key, save_key
from prospection.storage.secret_box import SecretBox, UnreadableSecret


class EmptyKey(ValueError):
    """La clé collée est vide."""


class InvalidKey(ValueError):
    """La clé contient des caractères qu'aucun service n'utilise (copier-coller abîmé)."""


MAX_KEY_LENGTH = 512
_KEY_CHARACTERS = re.compile(r"[\x21-\x7e]+")


@dataclass(frozen=True)
class KeyStatus:
    service: Service
    saved_at: datetime | None
    readable: bool
    tested_at: datetime | None
    test_ok: bool | None
    test_message: str | None


def _is_readable(box: SecretBox, ciphertext: bytes) -> bool:
    try:
        box.decrypt(ciphertext)
    except UnreadableSecret:
        return False
    return True


def key_statuses(engine: Engine, box: SecretBox) -> list[KeyStatus]:
    """État de chaque clé, sans jamais exposer la clé elle-même."""
    statuses = []
    with engine.connect() as conn:
        for service in Service:
            stored = load_key(conn, service)
            if stored is None:
                statuses.append(KeyStatus(service, None, False, None, None, None))
                continue
            readable = _is_readable(box, stored.ciphertext)
            statuses.append(
                KeyStatus(
                    service,
                    stored.saved_at,
                    readable,
                    stored.tested_at,
                    stored.test_ok,
                    stored.test_message,
                )
            )
    return statuses


def store_key(engine: Engine, box: SecretBox, service: Service, raw: str, now: datetime) -> None:
    """Nettoie la clé collée (espaces, retours à la ligne), la chiffre et l'enregistre."""
    key = "".join(raw.split())
    if not key:
        raise EmptyKey
    if len(key) > MAX_KEY_LENGTH or not _KEY_CHARACTERS.fullmatch(key):
        raise InvalidKey
    with engine.begin() as conn:
        save_key(conn, service, box.encrypt(key), now)


def read_key(engine: Engine, box: SecretBox, service: Service) -> str | None:
    """Clé en clair, pour appeler le service seulement ; None si absente ou illisible."""
    with engine.connect() as conn:
        stored = load_key(conn, service)
    if stored is None:
        return None
    try:
        return box.decrypt(stored.ciphertext)
    except UnreadableSecret:
        return None


def remove_key(engine: Engine, service: Service) -> None:
    with engine.begin() as conn:
        delete_key(conn, service)
