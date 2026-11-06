"""Lien de fiche Google qui n'est pas un vrai site : réseau social, page de liens, annuaire
(C154). Le prospect compte alors comme « sans site »."""

from urllib.parse import urlsplit

from prospection.domain.site_signals import signals


def not_a_site(url: str) -> str | None:
    """Nom du service (« Instagram »…) si l'adresse n'est pas un vrai site, sinon None."""
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return next(
        (name for domain, name in signals().not_sites.items()
         if host == domain or host.endswith("." + domain)),
        None,
    )  # fmt: skip
