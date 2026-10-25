"""C82, C83 : l'en-tête d'IP est validé ; les IPv6 sont comptées par bloc /64."""

from starlette.requests import Request

from prospection.config import Settings
from prospection.ui.client_ip import client_ip


def request_with(real_ip: str | None) -> Request:
    headers = [] if real_ip is None else [(b"x-real-ip", real_ip.encode())]
    return Request({"type": "http", "headers": headers, "client": ("100.64.0.9", 1234)})


def test_valid_ipv4_is_used(settings: Settings) -> None:
    assert client_ip(request_with(" 203.0.113.7 "), settings) == "203.0.113.7"


def test_ipv6_is_grouped_by_64_block(settings: Settings) -> None:
    ip = client_ip(request_with("2001:db8:1:2:aaaa:bbbb:cccc:dddd"), settings)
    assert ip == "2001:db8:1:2::/64"


def test_junk_header_falls_back_to_connection_address(settings: Settings) -> None:
    assert client_ip(request_with("x" * 6400), settings) == "100.64.0.9"


def test_missing_header_falls_back_to_connection_address(settings: Settings) -> None:
    assert client_ip(request_with(None), settings) == "100.64.0.9"
