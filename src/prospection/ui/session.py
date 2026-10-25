"""Session signée de 30 jours, glissante (C01, C116)."""

import hashlib
from datetime import datetime, timedelta

from fastapi import Depends, Request
from itsdangerous import BadSignature, TimestampSigner

from prospection.config import Settings
from prospection.ui.deps import get_now, get_settings

COOKIE_NAME = "__Host-session"
MAX_AGE = timedelta(days=30)
REFRESH_AFTER = timedelta(days=1)
ABSOLUTE_MAX_AGE = timedelta(days=90)


class LoginRequired(Exception):
    def __init__(self, path: str) -> None:
        self.path = path


class _Signer(TimestampSigner):
    def __init__(self, settings: Settings, now: datetime) -> None:
        super().__init__(settings.session_secret.get_secret_value(), salt="session")
        self._now = now

    def get_timestamp(self) -> int:
        return int(self._now.timestamp())


def _fingerprint(settings: Settings) -> str:
    digest = hashlib.sha256(settings.app_password_hash.get_secret_value().encode())
    return digest.hexdigest()[:16]


def make_session_value(settings: Settings, now: datetime, issued_at: datetime | None = None) -> str:
    """Signe l'empreinte du mot de passe et la date de connexion (fixe)."""
    login_date = int((issued_at or now).timestamp())
    payload = f"{_fingerprint(settings)}:{login_date}"
    return _Signer(settings, now).sign(payload).decode()


def read_session(settings: Settings, value: str, now: datetime) -> tuple[datetime, datetime] | None:
    """Rend (date de signature, date de connexion) si la session est valide, sinon None.

    Valide = signature correcte, utilisée depuis moins de 30 jours, connexion de
    moins de 90 jours (une session volée finit par expirer), même mot de passe.
    """
    try:
        content, signed_at = _Signer(settings, now).unsign(
            value, max_age=int(MAX_AGE.total_seconds()), return_timestamp=True
        )
        fingerprint, login_date = content.decode().split(":")
        issued_at = datetime.fromtimestamp(int(login_date), tz=signed_at.tzinfo)
    except (BadSignature, ValueError):
        return None
    if fingerprint != _fingerprint(settings) or now - issued_at > ABSOLUTE_MAX_AGE:
        return None
    return signed_at, issued_at


def require_session(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> None:
    session = read_session(settings, request.cookies.get(COOKIE_NAME, ""), now)
    if session is None:
        raise LoginRequired(request.url.path)
    signed_at, issued_at = session
    if now - signed_at > REFRESH_AFTER:
        request.state.new_session = make_session_value(settings, now, issued_at)
