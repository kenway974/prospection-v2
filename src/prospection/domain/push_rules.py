"""Notifications sur le téléphone (C108, C98, C99…) : quand envoyer, vers où, quoi."""

from datetime import datetime
from urllib.parse import urlsplit

from prospection.domain.text import without_controls

# Services de notification des navigateurs (Chrome, Firefox, Edge, Safari) : l'adresse
# d'abonnement vient du téléphone, le serveur n'appelle jamais autre chose (SSRF).
PUSH_HOSTS = ("fcm.googleapis.com", "push.services.mozilla.com", "notify.windows.com",
              "push.apple.com")  # fmt: skip
ALWAYS = frozenset({"relance"})  # une relance part même pendant les heures calmes
MAX_BODY = 180


def allowed_endpoint(url: str) -> bool:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    known = any(host == h or host.endswith(f".{h}") for h in PUSH_HOSTS)
    return parts.scheme == "https" and port in (None, 443) and known and len(url) <= 1000


def quiet(now_local: datetime, start: int, end: int) -> bool:
    """Heures calmes de `start` h à `end` h (passe minuit si start > end) ; start == end :
    aucune."""
    hour = now_local.hour
    if start == end:
        return False
    return start <= hour < end if start < end else hour >= start or hour < end


def may_send(kind: str, now_local: datetime, start: int, end: int) -> bool:
    return kind in ALWAYS or not quiet(now_local, start, end)


def notification_text(message: str) -> str:
    """Texte court, sans caractère de contrôle (un nom vient de Google ou d'un site)."""
    clean = " ".join(without_controls(message).split())
    return clean if len(clean) <= MAX_BODY else clean[: MAX_BODY - 1] + "…"


def safe_link(link: str) -> str:
    """Seulement un chemin de l'app : jamais une adresse extérieure."""
    return link if link.startswith("/") and not link.startswith("//") else "/"
