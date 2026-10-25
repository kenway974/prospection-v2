"""Adresse IP du visiteur, pour le journal et la limite d'essais (C82, C83)."""

from starlette.requests import Request

from prospection.config import Settings


def client_ip(request: Request, settings: Settings) -> str:
    """Derrière Railway, X-Real-IP porte l'IP du client.

    Le proxy de Railway écrase cet en-tête à chaque requête : un visiteur ne peut
    pas le choisir. Sans proxy, les en-têtes sont ignorés.
    """
    if settings.behind_proxy:
        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip
    return request.client.host if request.client else "inconnue"
