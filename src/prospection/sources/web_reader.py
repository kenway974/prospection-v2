"""Lire la page d'accueil d'un site, bornée en taille et en durée (C87, C88, règle 4).

Seuls http(s) sur les ports standard et un nom de domaine sont acceptés ; chaque redirection
est revérifiée ; la connexion elle-même passe par la garde de `safe_network`.
"""

import ipaddress
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 500_000
MAX_SECONDS = 8.0
MAX_REDIRECTS = 3
_LOCAL_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home", ".arpa")


@dataclass(frozen=True)
class WebPage:
    url: str  # adresse finale, après redirections
    html: str
    seconds: float


@dataclass(frozen=True)
class ReadResult:
    page: WebPage | None
    problem: str | None = None


def allowed_url(url: str) -> bool:
    """http(s), port standard, nom de domaine public (jamais une IP ni un nom local)."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in ("http", "https") or not host or parts.username or parts.password:
        return False
    if port not in (None, 80, 443) or "." not in host or host.endswith(_LOCAL_SUFFIXES):
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return True
    return False


def read_page(
    client: httpx.Client, url: str, clock: Callable[[], float] = time.monotonic
) -> ReadResult:
    """La page HTML du site, ou le problème rencontré, dit simplement."""
    start = clock()
    for _ in range(MAX_REDIRECTS + 1):
        if not allowed_url(url):
            return ReadResult(None, "Adresse du site refusée")
        try:
            with client.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("Location", ""))
                    continue
                if response.status_code >= 400:
                    return ReadResult(None, f"Le site répond une erreur {response.status_code}")
                if "html" not in response.headers.get("Content-Type", "text/html").lower():
                    return ReadResult(None, "L'adresse n'est pas une page web")
                body = b""
                for chunk in response.iter_bytes():
                    body += chunk
                    if clock() - start > MAX_SECONDS:
                        return ReadResult(None, "Site trop lent : lecture abandonnée")
                    if len(body) >= MAX_BYTES:
                        break
                seconds = clock() - start
                if seconds > MAX_SECONDS:
                    return ReadResult(None, "Site trop lent : lecture abandonnée")
                text = body[:MAX_BYTES].decode(response.encoding or "utf-8", errors="replace")
                return ReadResult(WebPage(url, text[:MAX_BYTES], seconds))
        except (httpx.HTTPError, UnicodeError, LookupError):
            return ReadResult(None, "Site injoignable")
    return ReadResult(None, "Trop de redirections")
