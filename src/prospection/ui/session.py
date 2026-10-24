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


def make_session_value(settings: Settings, now: datetime) -> str:
    return _Signer(settings, now).sign(_fingerprint(settings)).decode()


def session_signed_at(settings: Settings, value: str, now: datetime) -> datetime | None:
    """Rend la date de signature si la session est valide, sinon None."""
    try:
        content, signed_at = _Signer(settings, now).unsign(
            value, max_age=int(MAX_AGE.total_seconds()), return_timestamp=True
        )
    except BadSignature:
        return None
    return signed_at if content.decode() == _fingerprint(settings) else None


def require_session(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> None:
    signed_at = session_signed_at(settings, request.cookies.get(COOKIE_NAME, ""), now)
    if signed_at is None:
        raise LoginRequired(request.url.path)
    if now - signed_at > REFRESH_AFTER:
        request.state.new_session = make_session_value(settings, now)
