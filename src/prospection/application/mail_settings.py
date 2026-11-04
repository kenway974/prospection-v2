"""Réglages du mail d'audit et connexion Gmail (C144).

Le jeton de connexion Gmail est chiffré en base (règle 6) et ne s'affiche jamais ; seule
l'adresse du compte relié est montrée.
"""

import secrets
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.domain.mail_settings import MailSettings, clean_mail_settings
from prospection.sources.gmail import GmailOAuth, authorize_url, exchange_code
from prospection.storage import mail_settings as store
from prospection.storage.secret_box import SecretBox, UnreadableSecret

REDIRECT_PATH = "/reglages/gmail/retour"


def load_settings_screen(engine: Engine) -> MailSettings:
    with engine.connect() as conn:
        return store.load_mail_settings(conn)


def change_mail_settings(
    engine: Engine, name: str, phone: str, portfolio: str, calendly: str, days: str
) -> None:
    """InvalidMailSettings (champ → message) si une saisie est refusée ; rien n'est changé."""
    settings = clean_mail_settings(name, phone, portfolio, calendly, days)
    with engine.begin() as conn:
        store.save_mail_settings(conn, settings)


def connected_address(engine: Engine) -> str | None:
    with engine.connect() as conn:
        account = store.load_gmail(conn)
    return account.address if account else None


def start_gmail(oauth: GmailOAuth, base: str) -> tuple[str, str]:
    """Adresse de la page d'accord Google et état à vérifier au retour (anti-falsification)."""
    state = secrets.token_urlsafe(24)
    return authorize_url(oauth, base + REDIRECT_PATH, state), state


def finish_gmail(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth, base: str,
    code: str, now: datetime,
) -> str:  # fmt: skip
    """Échange le code contre un jeton durable, le chiffre et l'enregistre ; rend l'adresse."""
    grant = exchange_code(client, oauth, code, base + REDIRECT_PATH)
    with engine.begin() as conn:
        store.save_gmail(conn, grant.address, box.encrypt(grant.refresh_token), now)
    return grant.address


def gmail_refresh_token(engine: Engine, box: SecretBox) -> str | None:
    with engine.connect() as conn:
        account = store.load_gmail(conn)
    if account is None:
        return None
    try:
        return box.decrypt(account.token)
    except UnreadableSecret:
        return None


def disconnect_gmail(engine: Engine) -> None:
    with engine.begin() as conn:
        store.save_gmail(conn, None, None, None)
