"""Configuration lue dans les variables d'environnement de l'hébergeur."""

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError
from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    from prospection.application.backup import BackupTarget
    from prospection.sources.web_push import VapidKeys

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
    test_services_url: str | None = None  # bout en bout seulement : faux services locaux
    sentry_dsn: SecretStr | None = None  # C100 : erreurs remontées, si défini
    # C91 : stockage compatible S3 des sauvegardes (https://<compte>.r2.cloudflarestorage.com/<seau>)
    backup_s3_url: str | None = None
    backup_s3_access_key: SecretStr | None = None
    backup_s3_secret_key: SecretStr | None = None
    backup_s3_region: str = "auto"
    # Notifications sur le téléphone : python -m prospection.cli generate-vapid-keys
    vapid_public_key: str | None = None
    vapid_private_key: SecretStr | None = None
    vapid_subject: str | None = None  # mailto:vous@exemple.fr

    @field_validator("backup_s3_url")
    @classmethod
    def _backup_url_is_https(cls, url: str | None) -> str | None:
        if url is not None and urlsplit(url).scheme != "https":
            raise ValueError("adresse https:// attendue")
        return url

    def backup_target(self) -> "BackupTarget | None":
        """Stockage des sauvegardes, s'il est entièrement configuré."""
        from prospection.application.backup import BackupTarget

        if not (self.backup_s3_url and self.backup_s3_access_key and self.backup_s3_secret_key):
            return None
        access, secret = self.backup_s3_access_key, self.backup_s3_secret_key
        return BackupTarget(self.backup_s3_url, access.get_secret_value(),
                            secret.get_secret_value(), self.backup_s3_region)  # fmt: skip

    def vapid_keys(self) -> "VapidKeys | None":
        """Clés des notifications, si elles sont toutes définies."""
        from prospection.sources.web_push import VapidKeys

        if not (self.vapid_public_key and self.vapid_private_key and self.vapid_subject):
            return None
        private = self.vapid_private_key.get_secret_value()
        return VapidKeys(private, self.vapid_public_key, self.vapid_subject)

    @field_validator("vapid_subject")
    @classmethod
    def _vapid_subject_is_contact(cls, subject: str | None) -> str | None:
        if subject is not None and not subject.startswith(("mailto:", "https://")):
            raise ValueError("mailto:vous@exemple.fr attendu")
        return subject

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

    @field_validator("test_services_url")
    @classmethod
    def _test_url_stays_local(cls, url: str | None, info: ValidationInfo) -> str | None:
        """Les clés (Google, INSEE) ne partent que vers de faux services locaux, jamais en prod."""
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
