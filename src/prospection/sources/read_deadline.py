"""Échéance unique pour la lecture d'un site (C88).

Le délai par opération de httpx repart à chaque octet reçu : un serveur qui envoie ses
en-têtes un octet à la fois tiendrait des jours. Ici, chaque lecture et écriture sur le
réseau est bornée par le temps restant avant l'échéance fixée pour toute la lecture.
"""

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import httpcore

_local = threading.local()


def current_deadline() -> float | None:
    return getattr(_local, "at", None)


@contextmanager
def deadline(seconds: float) -> Iterator[None]:
    """Échéance unique pour tout ce qui suit dans ce fil : DNS, connexion, TLS, en-têtes,
    corps et redirections. Un serveur qui envoie un octet à la fois ne la repousse pas."""
    previous = current_deadline()
    _local.at = time.monotonic() + seconds
    try:
        yield
    finally:
        _local.at = previous


def remaining(at: float | None, clock: Callable[[], float], timeout: float | None) -> float | None:
    if at is None:
        return timeout
    left = at - clock()
    if left <= 0:
        raise httpcore.ReadTimeout("échéance de lecture dépassée")
    return left if timeout is None else min(timeout, left)


class DeadlineStream(httpcore.NetworkStream):
    """Chaque lecture et écriture est bornée par l'échéance restante, pas seulement par le
    délai par opération (qui repart à chaque octet reçu)."""

    def __init__(
        self, inner: httpcore.NetworkStream, deadline: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:  # fmt: skip
        self.inner, self.at, self.clock = inner, deadline, clock

    def _left(self, timeout: float | None) -> float | None:
        at = self.at if self.at is not None else current_deadline()
        return remaining(at, self.clock, timeout)

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return self.inner.read(max_bytes, self._left(timeout))

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        self.inner.write(buffer, self._left(timeout))

    def close(self) -> None:
        self.inner.close()

    def start_tls(
        self, ssl_context: Any, server_hostname: str | None = None, timeout: float | None = None
    ) -> httpcore.NetworkStream:
        tls = self.inner.start_tls(ssl_context, server_hostname, self._left(timeout))
        return DeadlineStream(tls, self.at, self.clock)

    def get_extra_info(self, info: str) -> Any:
        return self.inner.get_extra_info(info)


class BlockedAddress(httpcore.ConnectError):
    """Le site pointe vers une adresse interne, ou son nom est inconnu."""
