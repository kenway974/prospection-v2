"""C85 : les clés API sont chiffrées ; une mauvaise clé de chiffrement est détectée."""

import pytest
from cryptography.fernet import Fernet

from prospection.storage.secret_box import SecretBox, UnreadableSecret


def test_C85_ciphertext_does_not_contain_the_key() -> None:
    box = SecretBox(Fernet.generate_key().decode())
    token = box.encrypt("AIza-secret-123")
    assert b"AIza-secret-123" not in token
    assert box.decrypt(token) == "AIza-secret-123"


def test_C85_wrong_key_raises_unreadable() -> None:
    token = SecretBox(Fernet.generate_key().decode()).encrypt("AIza-secret-123")
    with pytest.raises(UnreadableSecret):
        SecretBox(Fernet.generate_key().decode()).decrypt(token)
