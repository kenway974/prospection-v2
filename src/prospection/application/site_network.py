"""Lien de fiche Google qui n'est pas le site de l'entreprise : réseau social, annuaire connu
(C154), ou domaine partagé par plusieurs entreprises, donc une plateforme ou un réseau (C174)."""

from collections.abc import Callable
from urllib.parse import urlsplit

from prospection.domain.not_site import not_a_site

MIN_SHARED = 3  # entreprises différentes (celle-ci comprise) sur un même domaine
Shared = Callable[[str, str], int]  # domaine, nom de l'entreprise → autres entreprises


def network_of(url: str, name: str, shared: Shared | None) -> str | None:
    """Nom du service ou du domaine partagé, sinon None (vrai site possible)."""
    if known := not_a_site(url):
        return known
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    if shared is None or not host:
        return None
    others = shared(host, name)
    if others + 1 < MIN_SHARED:
        return None
    return f"{host}, un site partagé par plusieurs entreprises ({others + 1})"
