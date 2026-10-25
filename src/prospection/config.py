"""Configuration lue dans les variables d'environnement de l'hébergeur."""

from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError
from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings


class ConfigError(Exception):
    """Une variable d'environnement manque ou est invalide."""


class Settings(BaseSettings):
    database_url: str
    session_secret: SecretStr = Field(min_length=32)
    app_password_hash: SecretStr
    encryption_key: SecretStr
    behind_proxy: bool = True
    timezone: str = "Europe/Paris"

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


def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as error:
        names = ", ".join(str(e["loc"][0]).upper() for e in error.errors())
        raise ConfigError(
            f"Variable d'environnement manquante ou invalide : {names}. "
            "Définissez-la dans Railway (ou dans .env en local), voir .env.example."
        ) from None
