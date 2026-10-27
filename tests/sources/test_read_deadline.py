"""C88 : une seule échéance pour toute la lecture d'un site ; DNS borné."""

import httpcore
import pytest

from prospection.sources.read_deadline import DeadlineStream
from prospection.sources.safe_network import BlockedAddress, PublicOnly
from tests.sources.test_safe_network import FakeBackend, backend


class SlowStream(httpcore.NetworkStream):
    """Serveur qui envoie un octet à la fois ; l'horloge avance d'une seconde par lecture."""

    def __init__(self, clock: list[float]) -> None:
        self.clock, self.timeouts = clock, []  # type: ignore[var-annotated]

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        self.timeouts.append(timeout)
        self.clock[0] += 1
        return b"x"

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        pass

    def close(self) -> None:
        pass


def test_C88_one_deadline_for_the_whole_reading() -> None:
    """Octet par octet, chaque lecture est courte : c'est l'échéance totale qui arrête."""
    clock = [0.0]
    stream = DeadlineStream(SlowStream(clock), deadline=3.0, clock=lambda: clock[0])
    with pytest.raises(httpcore.ReadTimeout):
        for _ in range(10):
            stream.read(1, timeout=5)
    assert clock[0] == 3.0  # 3 lectures, pas 10
    assert stream.inner.timeouts[0] == 3.0  # type: ignore[attr-defined]


def test_C88_slow_name_resolution_bounded() -> None:
    import threading

    gate = threading.Event()

    def stuck(host: str) -> list[str]:
        gate.wait(5)
        return ["93.184.215.14"]

    safe = PublicOnly(resolve=stuck, inner=FakeBackend(), resolve_seconds=0.2)
    with pytest.raises(BlockedAddress):
        safe.connect_tcp("lent.fr", 443)
    gate.set()


def test_C88_stuck_lookups_never_starve_the_others() -> None:
    """Des résolutions bloquées et abandonnées ne prennent la place d'aucune autre."""
    import threading

    gate = threading.Event()

    def stuck(host: str) -> list[str]:
        gate.wait(10)
        return []

    blocked = PublicOnly(resolve=stuck, inner=FakeBackend(), resolve_seconds=0.05)
    for _ in range(12):
        with pytest.raises(BlockedAddress):
            blocked.connect_tcp("lent.fr", 443)
    safe, inner = backend("93.184.215.14")
    safe.resolve_seconds = 0.5
    with pytest.raises(httpcore.ConnectError):
        safe.connect_tcp("martin.fr", 443)
    assert inner.connected == [("93.184.215.14", 443)]
    gate.set()
