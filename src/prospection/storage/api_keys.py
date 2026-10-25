"""Clés API chiffrées et résultat de leur dernier test (C02, C03, C85)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, delete, select, update
from sqlalchemy.dialects.postgresql import insert

from prospection.domain.services import Service
from prospection.storage.db import api_keys


@dataclass(frozen=True)
class StoredKey:
    service: Service
    ciphertext: bytes
    saved_at: datetime
    tested_at: datetime | None
    test_ok: bool | None
    test_message: str | None


def save_key(conn: Connection, service: Service, ciphertext: bytes, now: datetime) -> None:
    """Enregistre (ou remplace) la clé ; le résultat du test précédent est effacé."""
    values = {
        "ciphertext": ciphertext,
        "saved_at": now,
        "tested_at": None,
        "test_ok": None,
        "test_message": None,
    }
    statement = insert(api_keys).values(service=service.value, **values)
    conn.execute(statement.on_conflict_do_update(index_elements=["service"], set_=values))


def load_key(conn: Connection, service: Service) -> StoredKey | None:
    row = conn.execute(select(api_keys).where(api_keys.c.service == service.value)).first()
    if row is None:
        return None
    return StoredKey(
        Service(row.service),
        bytes(row.ciphertext),
        row.saved_at,
        row.tested_at,
        row.test_ok,
        row.test_message,
    )


def record_test(conn: Connection, service: Service, now: datetime, ok: bool, message: str) -> None:
    conn.execute(
        update(api_keys)
        .where(api_keys.c.service == service.value)
        .values(tested_at=now, test_ok=ok, test_message=message)
    )


def delete_key(conn: Connection, service: Service) -> None:
    conn.execute(delete(api_keys).where(api_keys.c.service == service.value))
