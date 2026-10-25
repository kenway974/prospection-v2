"""Chiffrement des clés API en base (C85). La clé vient de l'environnement (C86)."""

from cryptography.fernet import Fernet, InvalidToken


class UnreadableSecret(Exception):
    """Le secret ne se déchiffre pas (clé de chiffrement changée ou donnée abîmée)."""


class SecretBox:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, plain: str) -> bytes:
        return self._fernet.encrypt(plain.encode())

    def decrypt(self, token: bytes) -> str:
        try:
            return self._fernet.decrypt(token).decode()
        except InvalidToken:
            raise UnreadableSecret from None
