"""Réglages → SMS (C175) : réglages enregistrés et présence de la clé Brevo."""

from dataclasses import dataclass

from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.domain.services import Service
from prospection.domain.sms_settings import SmsSettings, clean_sms_settings
from prospection.storage.secret_box import SecretBox
from prospection.storage.sms_settings_store import load_sms_settings, save_sms_settings


@dataclass(frozen=True)
class SmsSettingsScreen:
    settings: SmsSettings
    has_key: bool


def sms_settings_screen(engine: Engine, box: SecretBox) -> SmsSettingsScreen:
    with engine.connect() as conn:
        settings = load_sms_settings(conn)
    return SmsSettingsScreen(settings, read_key(engine, box, Service.BREVO) is not None)


def change_sms_settings(engine: Engine, enabled: str, sender: str, limit: str) -> None:
    """InvalidSmsSettings si une saisie est refusée ; rien n'est alors changé."""
    settings = clean_sms_settings(enabled, sender, limit)
    with engine.begin() as conn:
        save_sms_settings(conn, settings)
