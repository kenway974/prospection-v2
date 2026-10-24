"""Hachage du mot de passe d'accès (argon2id)."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(hash_: str, plain: str) -> bool:
    try:
        return _hasher.verify(hash_, plain)
    except (VerificationError, InvalidHashError):
        return False
