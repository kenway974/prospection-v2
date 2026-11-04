"""C144, C146 : identifiants Google de l'app et adresse publique (liens du mail)."""

import pytest
from pydantic import ValidationError

from prospection.config import Settings
from prospection.sources.gmail import GmailOAuth
from tests.test_config import FERNET_KEY, VALID_HASH

BASE = {"database_url": "postgresql+psycopg://localhost/x", "session_secret": "s" * 32,
        "app_password_hash": VALID_HASH, "encryption_key": FERNET_KEY}  # fmt: skip


def make(**values: str) -> Settings:
    return Settings(**{**BASE, **values})  # type: ignore[arg-type]


def test_C144_gmail_needs_both_identifiers() -> None:
    assert make().gmail_oauth() is None
    assert make(gmail_client_id="id").gmail_oauth() is None
    settings = make(gmail_client_id="id", gmail_client_secret="secret")
    assert settings.gmail_oauth() == GmailOAuth("id", "secret")


def test_C146_public_address_from_setting_or_railway() -> None:
    assert make().public_base() is None
    assert make(railway_public_domain="app.up.railway.app").public_base() == (
        "https://app.up.railway.app"
    )
    assert make(
        public_url="https://prospection.fr/", railway_public_domain="x.app"
    ).public_base() == ("https://prospection.fr")
    with pytest.raises(ValidationError):
        make(public_url="http://prospection.fr")
