"""C85 : les clés sont stockées chiffrées ; résultat du dernier test."""

from datetime import UTC, datetime

from cryptography.fernet import Fernet
from sqlalchemy import Connection, text

from prospection.domain.services import Service
from prospection.storage.api_keys import delete_key, load_key, record_test, save_key
from prospection.storage.secret_box import SecretBox

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
BOX = SecretBox(Fernet.generate_key().decode())


def test_C85_stored_key_is_encrypted_in_database(conn: Connection) -> None:
    save_key(conn, Service.GOOGLE, BOX.encrypt("AIza-secret-123"), NOW)
    raw = conn.execute(text("SELECT ciphertext FROM api_keys")).scalar_one()
    assert b"AIza-secret-123" not in bytes(raw)
    stored = load_key(conn, Service.GOOGLE)
    assert stored is not None
    assert BOX.decrypt(stored.ciphertext) == "AIza-secret-123"
    assert stored.saved_at == NOW


def test_record_and_reset_test_result(conn: Connection) -> None:
    save_key(conn, Service.NOTION, BOX.encrypt("secret_1"), NOW)
    record_test(conn, Service.NOTION, NOW, ok=True, message="Jeton Notion valide.")
    stored = load_key(conn, Service.NOTION)
    assert stored is not None
    assert (stored.tested_at, stored.test_ok, stored.test_message) == (
        NOW,
        True,
        "Jeton Notion valide.",
    )
    save_key(conn, Service.NOTION, BOX.encrypt("secret_2"), NOW)
    stored = load_key(conn, Service.NOTION)
    assert stored is not None
    assert (stored.tested_at, stored.test_ok, stored.test_message) == (None, None, None)


def test_missing_and_deleted_key(conn: Connection) -> None:
    assert load_key(conn, Service.INSEE) is None
    save_key(conn, Service.INSEE, BOX.encrypt("k"), NOW)
    delete_key(conn, Service.INSEE)
    assert load_key(conn, Service.INSEE) is None
