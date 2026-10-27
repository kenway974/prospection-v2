"""Connexions vers les sites des prospects : jamais vers une adresse interne (C87, règle 4).

Le nom est résolu une seule fois ; l'adresse vérifiée est celle à laquelle on se connecte
(pas de seconde résolution qui pourrait renvoyer une adresse interne : « DNS rebinding »).
Le certificat reste vérifié sur le nom du site. Amélioration de `prospection-bot`
(`services/site_finder.py::_safe_host`, version 530ba12), qui résolvait deux fois.
"""

import ipaddress
import socket
import threading
import time
from collections.abc import Callable, Iterable

import httpcore
import httpx

from prospection.sources.read_deadline import DeadlineStream, current_deadline, remaining

Resolver = Callable[[str], list[str]]
# NAT64, 6to4, Teredo, IPv4-compatible et SIIT transportent une adresse IPv4 ; site-local
# est interne : tous refusés d'office
_TRANSITION = tuple(
    ipaddress.IPv6Network(n)
    for n in ("64:ff9b::/96", "64:ff9b:1::/48", "2002::/16", "2001::/32", "::/96",
              "::ffff:0:0:0/96", "fec0::/10")
)  # fmt: skip


class BlockedAddress(httpcore.ConnectError):
    """Le site pointe vers une adresse interne, ou son nom est inconnu."""


def _system_resolve(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError):
        return []
    return [str(info[4][0]) for info in infos]


def is_public(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%")[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        elif any(ip in net for net in _TRANSITION):  # peut cacher une adresse IPv4 interne
            return False
    return ip.is_global and not ip.is_multicast


class PublicOnly(httpcore.NetworkBackend):
    """Résout le nom, refuse s'il mène à une seule adresse non publique, puis se connecte
    à l'adresse vérifiée."""

    def __init__(
        self, resolve: Resolver = _system_resolve, inner: httpcore.NetworkBackend | None = None,
        resolve_seconds: float = 5.0,
    ) -> None:  # fmt: skip
        self.resolve, self.resolve_seconds = resolve, resolve_seconds
        self.inner = inner or httpcore.SyncBackend()

    def _addresses(self, host: str) -> list[str]:
        """Résolution bornée dans le temps : un DNS muet ne bloque pas la lecture."""
        limit = remaining(current_deadline(), time.monotonic, self.resolve_seconds)
        found: list[list[str]] = []
        # Un fil par résolution : abandonnée, elle ne bloque la place d'aucune autre
        lookup = threading.Thread(target=lambda: found.append(self.resolve(host)), daemon=True)
        lookup.start()
        lookup.join(limit)
        return found[0] if found else []

    def connect_tcp(
        self, host: str, port: int, timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.NetworkStream:  # fmt: skip
        addresses = self._addresses(host)
        if not addresses or not all(is_public(a) for a in addresses):
            raise BlockedAddress("adresse interne ou inconnue")
        error: httpcore.ConnectError | httpcore.ConnectTimeout | None = None
        for address in dict.fromkeys(addresses):  # IPv6 sans sortie : l'IPv4 ensuite
            left = remaining(current_deadline(), time.monotonic, timeout)
            try:
                stream = self.inner.connect_tcp(address, port, left, local_address, socket_options)
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as failed:
                error = failed
                continue
            return DeadlineStream(stream)
        raise error or BlockedAddress("connexion impossible")

    def connect_unix_socket(
        self, path: str, timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.NetworkStream:  # fmt: skip
        raise BlockedAddress("connexion locale refusée")

    def sleep(self, seconds: float) -> None:
        self.inner.sleep(seconds)


class _SafeTransport(httpx.HTTPTransport):
    def __init__(self) -> None:
        super().__init__()
        # Même réserve de connexions que httpx, avec la garde ci-dessus pour se connecter
        self._pool = httpcore.ConnectionPool(
            ssl_context=httpx.create_ssl_context(), network_backend=PublicOnly(),
            max_connections=100, max_keepalive_connections=20, keepalive_expiry=5.0,
        )  # fmt: skip


class _AllToFake(httpx.BaseTransport):
    """Bout en bout seulement : chaque site est demandé au faux local (aucune vraie visite)."""

    def __init__(self, fake_url: str, inner: httpx.BaseTransport | None = None) -> None:
        self.fake, self.inner = httpx.URL(fake_url), inner or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.url = httpx.URL(str(self.fake.join("/site")), params={"url": str(request.url)})
        request.headers["Host"] = self.fake.netloc.decode()
        return self.inner.handle_request(request)


def make_web_client(
    test_services_url: str | None = None, inner: httpx.BaseTransport | None = None
) -> httpx.Client:
    """Client des sites : aucune variable de proxy suivie, aucune redirection automatique."""
    transport = _AllToFake(test_services_url, inner) if test_services_url else _SafeTransport()
    return httpx.Client(
        transport=transport, trust_env=False, follow_redirects=False, timeout=5.0,
        headers={"User-Agent": "Mozilla/5.0 (compatible; Prospection/2.0)"},
    )  # fmt: skip
