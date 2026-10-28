"""Le domaine d'un email déclare-t-il un serveur mail (MX) ? (C53)

Interroge le résolveur DNS du serveur (aucun tiers), avec un délai court. Pas de sonde
SMTP : port 25 fermé sur Railway, peu fiable, risque de liste noire.
"""

import re
from typing import Any, Protocol

import dns.exception
import dns.resolver

LIFETIME = 5.0
_DOMAIN = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){1,8}[a-z]{2,63}")


class Resolver(Protocol):
    def resolve(self, name: str, kind: str, lifetime: float) -> Any: ...


def mail_server(domain: str, resolver: Resolver | None = None) -> str | None:
    """« mx », « aucun » (domaine sans serveur mail), « inexistant », ou None (DNS muet :
    à revérifier plus tard, on ne condamne pas une adresse sur un aléa réseau)."""
    if len(domain) > 253 or not _DOMAIN.fullmatch(domain):
        return "inexistant"
    try:
        active = resolver or dns.resolver.Resolver()
        answer = active.resolve(domain, "MX", lifetime=LIFETIME)
    except dns.resolver.NXDOMAIN:
        return "inexistant"
    except dns.resolver.NoAnswer:
        return "mx" if _has_address(active, domain) else "aucun"  # MX implicite (RFC 5321)
    except (dns.exception.DNSException, OSError):  # dont SERVFAIL, souvent passager
        return None
    exchanges = [str(getattr(record, "exchange", "")).rstrip(".") for record in answer]
    return "aucun" if exchanges == [""] else "mx"  # « null MX » (RFC 7505) : aucun courrier


def _has_address(resolver: Resolver | dns.resolver.Resolver, domain: str) -> bool:
    for kind in ("A", "AAAA"):
        try:
            resolver.resolve(domain, kind, lifetime=LIFETIME)
        except (dns.exception.DNSException, OSError):
            continue
        return True
    return False
