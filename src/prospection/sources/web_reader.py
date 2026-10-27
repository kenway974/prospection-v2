"""Lire la page d'accueil d'un site, bornée en taille et en durée (C87, C88, règle 4).

Seuls http(s) sur les ports standard et un nom de domaine sont acceptés ; chaque redirection
est revérifiée ; la connexion elle-même passe par la garde de `safe_network`.
"""

import codecs
import ipaddress
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx

from prospection.sources.read_deadline import deadline

MAX_BYTES = 500_000
MAX_SECONDS = 8.0
MAX_REDIRECTS = 3
SLOW = "Site trop lent : lecture abandonnée"
_LOCAL_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home", ".arpa")
# Règle 2 (CGU) : jamais une page Google, même par redirection (anciens sites Google Business)
_GOOGLE = re.compile(
    r"(^|\.)(google\.[a-z.]+|g\.page|goo\.gl|business\.site|googleusercontent\.com)$"
)
_CHARSET = re.compile(rb"""<meta[^>]{0,200}charset=["']?([a-zA-Z0-9_-]{1,40})""", re.IGNORECASE)


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
    if _GOOGLE.search(host):
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return True
    return False


def _decode(body: bytes, header_charset: str | None) -> str:
    """Encodage de l'en-tête, sinon celui annoncé dans la page (vieux sites en latin-1)."""
    found = _CHARSET.search(body[:2048])
    for name in (header_charset, found.group(1).decode() if found else None, "utf-8"):
        try:
            if name and codecs.lookup(name):
                return body.decode(name, errors="replace")
        except LookupError:
            continue
    return body.decode("utf-8", errors="replace")


def read_page(
    client: httpx.Client, url: str, clock: Callable[[], float] = time.monotonic
) -> ReadResult:
    """La page HTML du site, ou le problème rencontré, dit simplement. Une seule échéance
    couvre DNS, connexion, en-têtes, corps et redirections (voir read_deadline)."""
    with deadline(MAX_SECONDS):
        return _read(client, url, clock)


def _read(client: httpx.Client, url: str, clock: Callable[[], float]) -> ReadResult:
    start = clock()
    for _ in range(MAX_REDIRECTS + 1):
        if not allowed_url(url):
            return ReadResult(None, "Adresse du site refusée")
        try:
            with client.stream("GET", url, headers={"Accept-Encoding": "identity"}) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("Location", ""))
                    continue
                if response.status_code >= 400:
                    return ReadResult(None, f"Le site répond une erreur {response.status_code}")
                if "html" not in response.headers.get("Content-Type", "text/html").lower():
                    return ReadResult(None, "L'adresse n'est pas une page web")
                if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                    return ReadResult(None, "Page compressée : non lue")  # bombe possible
                body = bytearray()
                for chunk in response.iter_raw():  # jamais décompressé : taille réelle bornée
                    body += chunk
                    if clock() - start > MAX_SECONDS:
                        return ReadResult(None, SLOW)
                    if len(body) >= MAX_BYTES:
                        break
                seconds = clock() - start
                if seconds > MAX_SECONDS:
                    return ReadResult(None, SLOW)
                text = _decode(bytes(body[:MAX_BYTES]), response.charset_encoding)
                return ReadResult(WebPage(url, text[:MAX_BYTES], seconds))
        except (httpx.TimeoutException, httpcore.TimeoutException):
            return ReadResult(None, SLOW)
        except (httpx.HTTPError, UnicodeError, LookupError):
            return ReadResult(None, "Site injoignable")
    return ReadResult(None, "Trop de redirections")
