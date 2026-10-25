"""Adresse IP du visiteur, pour le journal et la limite d'essais (C82, C83)."""

import ipaddress
import logging

from starlette.requests import Request

from prospection.config import Settings

logger = logging.getLogger(__name__)


def _normalize(value: str) -> str | None:
    """IP valide, ou None. Une IPv6 est ramenée à son bloc /64 (un abonné = un bloc)."""
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if address.version == 6:
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)


def client_ip(request: Request, settings: Settings) -> str:
    """Derrière Railway, X-Real-IP porte l'IP du client.

    Le proxy de Railway écrase cet en-tête à chaque requête : un visiteur ne peut
    pas le choisir. Sans proxy, ou si la valeur est invalide, on prend l'adresse
    de la connexion.
    """
    connection = request.client.host if request.client else "inconnue"
    if not settings.behind_proxy:
        return connection
    real_ip = _normalize(request.headers.get("x-real-ip", ""))
    if real_ip is None:
        logger.warning("En-tête X-Real-IP absent ou invalide derrière le proxy")
        return connection
    return real_ip
