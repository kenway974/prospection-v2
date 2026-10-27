"""C53 : serveur mail d'un domaine (MX), avec un faux résolveur (aucun réseau)."""

import dns.exception
import dns.resolver
import pytest

from prospection.sources.mail_domain import mail_server


class FakeResolver:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.asked: list[tuple[str, str]] = []

    def resolve(self, name: str, kind: str, lifetime: float) -> object:
        self.asked.append((name, kind))
        if isinstance(self.outcome, type) and issubclass(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [(["mx1.martin.fr"], "mx"), (dns.resolver.NXDOMAIN, "inexistant"),
     (dns.resolver.NoAnswer, "aucun"), (dns.resolver.NoNameservers, None),
     (dns.exception.Timeout, None)],
)  # fmt: skip
def test_C53_mail_server_of_a_domain(outcome: object, expected: str | None) -> None:
    resolver = FakeResolver(outcome)
    assert mail_server("martin.fr", resolver) == expected
    assert resolver.asked == [("martin.fr", "MX")]


@pytest.mark.parametrize("domain", ["", "martin", "a..fr", "x" * 300 + ".fr", "martin.fr/x"])
def test_odd_domain_never_asked(domain: str) -> None:
    resolver = FakeResolver(["mx"])
    assert mail_server(domain, resolver) == "inexistant" and resolver.asked == []
