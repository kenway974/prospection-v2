"""C87 : aucune connexion vers une adresse interne, même après résolution du nom."""

import httpcore
import httpx
import pytest

from prospection.sources.read_deadline import DeadlineStream
from prospection.sources.safe_network import BlockedAddress, PublicOnly, make_web_client


class FakeBackend(httpcore.NetworkBackend):
    def __init__(self) -> None:
        self.connected: list[tuple[str, int]] = []

    def connect_tcp(
        self, host: str, port: int, timeout: float | None = None,
        local_address: str | None = None, socket_options: object = None,
    ) -> httpcore.NetworkStream:  # fmt: skip
        self.connected.append((host, port))
        raise httpcore.ConnectError("faux réseau")


def backend(*addresses: str) -> tuple[PublicOnly, FakeBackend]:
    inner = FakeBackend()
    return PublicOnly(resolve=lambda host: list(addresses), inner=inner), inner


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "::ffff:127.0.0.1",
     "100.64.0.1", "0.0.0.0", "fd00::1",  # noqa: S104
     "64:ff9b::7f00:1", "64:ff9b:1::a00:5", "2002:7f00:1::1",
     "2001:0:4136:e378:8000:63bf:80ff:fffe"],
)  # fmt: skip
def test_C87_internal_address_never_connected(address: str) -> None:
    safe, inner = backend(address)
    with pytest.raises(BlockedAddress):
        safe.connect_tcp("site-piege.fr", 443)
    assert inner.connected == []


def test_C87_one_internal_address_among_public_ones_is_refused() -> None:
    safe, inner = backend("93.184.215.14", "10.0.0.5")
    with pytest.raises(BlockedAddress):
        safe.connect_tcp("site-piege.fr", 443)
    assert inner.connected == []


def test_C87_connects_to_the_checked_address_not_a_new_lookup() -> None:
    """L'adresse vérifiée est celle utilisée : pas de seconde résolution (DNS rebinding)."""
    safe, inner = backend("93.184.215.14")
    with pytest.raises(httpcore.ConnectError):
        safe.connect_tcp("boulangerie-martin.fr", 443)
    assert inner.connected == [("93.184.215.14", 443)]


def test_C87_unknown_name_is_refused() -> None:
    safe, _ = backend()
    with pytest.raises(BlockedAddress):
        safe.connect_tcp("inconnu.invalid", 443)


def test_C87_real_client_uses_the_guard_and_ignores_proxy_settings() -> None:
    client = make_web_client()
    pool = client._transport._pool  # type: ignore[attr-defined]
    assert isinstance(pool._network_backend, PublicOnly) and not client.trust_env
    assert not client.follow_redirects


def test_end_to_end_mode_never_visits_a_real_site() -> None:
    seen: list[httpx.Request] = []

    def fake(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(404)

    client = make_web_client("http://127.0.0.1:8099", inner=httpx.MockTransport(fake))
    client.get("https://boulangerie-martin.fr/")
    assert seen[0].url.host == "127.0.0.1" and seen[0].url.path == "/site"
    assert seen[0].url.params["url"] == "https://boulangerie-martin.fr/"


@pytest.mark.parametrize("address", ["::7f00:1", "::ffff:0:7f00:1", "fec0::1"])
def test_C87_rare_ipv6_forms_refused(address: str) -> None:
    safe, inner = backend(address)
    with pytest.raises(BlockedAddress):
        safe.connect_tcp("site-piege.fr", 443)
    assert inner.connected == []


def test_each_checked_address_tried_in_turn() -> None:
    """Pas d'IPv6 en sortie : l'adresse IPv4 vérifiée est essayée ensuite."""
    safe, inner = backend("2606:2800:220:1::1", "93.184.215.14")
    with pytest.raises(httpcore.ConnectError):
        safe.connect_tcp("martin.fr", 443)
    assert inner.connected == [("2606:2800:220:1::1", 443), ("93.184.215.14", 443)]


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


def test_pool_large_enough_for_parallel_reading() -> None:
    pool = make_web_client()._transport._pool  # type: ignore[attr-defined]
    assert pool._max_connections >= 16 and pool._keepalive_expiry == 5.0
