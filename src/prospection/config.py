"""Configuration lue dans les variables d'environnement de l'hébergeur."""

from urllib.parse import urlsplit

from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError
from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings

LOCAL_HOSTS = ("127.0.0.1", "localhost")


class ConfigError(Exception):
    """Une variable d'environnement manque ou est invalide."""


class Settings(BaseSettings):
    database_url: str
    session_secret: SecretStr = Field(min_length=32)
    app_password_hash: SecretStr
    encryption_key: SecretStr
    behind_proxy: bool = True
    timezone: str = "Europe/Paris"
    google_places_test_url: str | None = None  # bout en bout seulement : faux Google local

    @field_validator("app_password_hash")
    @classmethod
    def _is_argon2_hash(cls, value: SecretStr) -> SecretStr:
        try:
            extract_parameters(value.get_secret_value())
        except InvalidHashError:
            raise ValueError("hash argon2 attendu") from None
        return value

    @field_validator("encryption_key")
    @classmethod
    def _is_fernet_key(cls, value: SecretStr) -> SecretStr:
        try:
            Fernet(value.get_secret_value().encode())
        except ValueError:
            raise ValueError("clé Fernet attendue") from None
        return value

    @field_validator("google_places_test_url")
    @classmethod
    def _test_url_stays_local(cls, url: str | None, info: ValidationInfo) -> str | None:
        """La clé Google ne doit partir que vers un faux Google local, jamais en production."""
        if url is None:
            return None
        parts = urlsplit(url)
        behind_proxy = info.data.get("behind_proxy", True)
        if behind_proxy or parts.scheme != "http" or parts.hostname not in LOCAL_HOSTS:
            raise ValueError("http://127.0.0.1:port seulement, avec BEHIND_PROXY=false")
        return url


def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as error:
        names = ", ".join(str(e["loc"][0]).upper() for e in error.errors())
        raise ConfigError(
            f"Variable d'environnement manquante ou invalide : {names}. "
            "Définissez-la dans Railway (ou dans .env en local), voir .env.example."
        ) from None
