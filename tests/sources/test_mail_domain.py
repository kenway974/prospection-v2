"""C53 : serveur mail d'un domaine (MX), avec un faux résolveur (aucun réseau)."""

import dns.exception
import dns.resolver
import pytest

from prospection.sources.mail_domain import mail_server


class Mx:
    def __init__(self, exchange: str) -> None:
        self.exchange = exchange


class FakeResolver:
    """Réponses par type d'enregistrement ; une classe d'exception est levée."""

    def __init__(self, outcome: object, address: object = dns.resolver.NoAnswer) -> None:
        self.answers = {"MX": outcome, "A": address, "AAAA": dns.resolver.NoAnswer}
        self.asked: list[tuple[str, str]] = []

    def resolve(self, name: str, kind: str, lifetime: float) -> object:
        self.asked.append((name, kind))
        answer = self.answers[kind]
        if isinstance(answer, type) and issubclass(answer, BaseException):
            raise answer
        return answer


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [([Mx("mx1.martin.fr.")], "mx"), (dns.resolver.NXDOMAIN, "inexistant"),
     (dns.resolver.NoAnswer, "aucun"), (dns.resolver.NoNameservers, None),
     (dns.exception.Timeout, None)],
)  # fmt: skip
def test_C53_mail_server_of_a_domain(outcome: object, expected: str | None) -> None:
    resolver = FakeResolver(outcome)
    assert mail_server("martin.fr", resolver) == expected
    assert resolver.asked[0] == ("martin.fr", "MX")


@pytest.mark.parametrize("domain", ["", "martin", "a..fr", "x" * 300 + ".fr", "martin.fr/x"])
def test_odd_domain_never_asked(domain: str) -> None:
    resolver = FakeResolver([Mx("mx.")])
    assert mail_server(domain, resolver) == "inexistant" and resolver.asked == []


def test_C53_no_mx_but_an_address_receives_mail() -> None:
    """MX implicite (RFC 5321) : un domaine sans MX mais avec une adresse reçoit le courrier."""
    assert mail_server("martin.fr", FakeResolver(dns.resolver.NoAnswer, ["1.2.3.4"])) == "mx"


def test_C53_null_mx_refuses_mail() -> None:
    """« null MX » (RFC 7505) : le domaine annonce qu'il ne reçoit aucun courrier."""
    assert mail_server("martin.fr", FakeResolver([Mx(".")])) == "aucun"


def test_missing_resolver_configuration_is_not_a_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> object:
        raise dns.resolver.NoResolverConfiguration

    monkeypatch.setattr(dns.resolver, "Resolver", broken)
    assert mail_server("martin.fr") is None
