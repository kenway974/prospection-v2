"""À qui appartient une adresse lue sur un site (C187, C188).

Une adresse déguisée ou lue dans les mentions légales n'est gardée que si elle est sur le
domaine du site (avec ou sans www) ou chez une messagerie grand public : jamais celle de
l'hébergeur ni de l'agence qui a fait le site, qui recevraient l'audit à la place du prospect.
"""

from urllib.parse import urlsplit

from prospection.domain.site_signals import signals


def site_host(url: str) -> str:
    """Nom du site sans « www. » ; vide si l'adresse n'en a pas."""
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def same_site(url: str, other: str) -> bool:
    host = site_host(url)
    return bool(host) and host == site_host(other)


def own_address(email: str, site: str) -> bool:
    domain = email.rsplit("@", 1)[-1].lower().removeprefix("www.")
    return domain == site_host(site) or domain in signals().webmail_domains
