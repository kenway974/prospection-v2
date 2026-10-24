"""Configuration lue dans les variables d'environnement de l'hébergeur."""

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings


class ConfigError(Exception):
    """Une variable d'environnement manque ou est invalide."""


class Settings(BaseSettings):
    database_url: str
    session_secret: SecretStr = Field(min_length=32)
    app_password_hash: SecretStr
    behind_proxy: bool = True
    timezone: str = "Indian/Reunion"


def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as error:
        names = ", ".join(str(e["loc"][0]).upper() for e in error.errors())
        raise ConfigError(
            f"Variable d'environnement manquante ou invalide : {names}. "
            "Définissez-la dans Railway (ou dans .env en local), voir .env.example."
        ) from None
