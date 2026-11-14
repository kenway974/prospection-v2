"""Contacts publiés sur le site de l'entreprise : emails, téléphones, pages sociales (C48).

Repris de prospection-bot (services/analyzer.py::_scrape_email, version 530ba12), élargi aux
téléphones et aux pages de l'entreprise. Jamais un profil personnel LinkedIn ni un bouton de
partage. Rien n'est vérifié ici (envoi interdit : on lit seulement ce qui est publié).
"""

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

import phonenumbers

from prospection.domain.email_check import is_email
from prospection.domain.email_owner import own_address
from prospection.domain.html_page import Page
from prospection.domain.place import web_link

MAX_FOUND = 5
_LOCAL = re.compile(r"[a-z0-9._%+-]{1,64}$", re.IGNORECASE)
_DOMAIN = re.compile(r"[a-z0-9.-]{1,200}\.[a-z]{2,24}", re.IGNORECASE)
MAX_AT = 50
MAX_TEL_LINKS = 20
_IGNORED = ("example.", "sentry", "wixpress", "wix.com", "domain.", "email.com", "votre")
_IMAGE = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
# Pages d'entreprise : (domaine, début de chemin exigé, débuts de chemin refusés)
_SOCIAL = (
    (
        "facebook.com",
        "/",
        (
            "/sharer",
            "/share",
            "/plugins",
            "/dialog",
            "/tr",
            "/login",
            "/profile.php",
            "/groups",
            "/events",
            "/people",
        ),
    ),
    ("instagram.com", "/", ("/p/", "/reel", "/explore", "/accounts")),
    ("linkedin.com", "/company/", ()),
)


@dataclass(frozen=True)
class Contacts:
    emails: tuple[str, ...]
    phones: tuple[str, ...]  # format international
    social: tuple[str, ...]


def _unique(items: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))[:MAX_FOUND]


# C187 : « contact [at] domaine [dot] fr », « contact(at)domaine.fr » (jamais « mot @ site.fr »,
# trop courant dans un texte ordinaire : « Réalisé par Studio @ agence.fr »)
_AT = re.compile(r"\s*[\[(]\s*(?:at|arobase|@)\s*[\])]\s*", re.IGNORECASE)
_DOT = re.compile(r"\s*[\[(]\s*(?:dot|point)\s*[\])]\s*", re.IGNORECASE)


def _undisguised(text: str) -> str:
    """Adresses déguisées remises en clair ; un texte sans déguisement reste le même."""
    return _DOT.sub(".", _AT.sub("@", text))


def _in_text(text: str) -> list[str]:
    """Adresses lues autour de chaque « @ », dans une fenêtre bornée : coût linéaire, même
    sur une très longue suite de lettres (une recherche directe serait quadratique)."""
    found: list[str] = []
    at = text.find("@")
    while at != -1 and len(found) < MAX_AT:
        start = max(0, at - 64)
        local, domain = _LOCAL.search(text[start:at]), _DOMAIN.match(text, at + 1)
        cut = (
            local is not None
            and start + local.start() > 0
            and text[start + local.start() - 1].isalpha()
        )
        if local and domain and not cut:  # jamais une adresse coupée dans un mot (« équipe@ »)
            found.append(f"{local.group()}@{domain.group()}")
        at = text.find("@", at + 1)
    return found


def _emails(page: Page, site: str) -> tuple[str, ...]:
    mailtos = [
        unquote(link[7:].split("?")[0]) for link in page.links if link.lower().startswith("mailto:")
    ]
    plain = _in_text(page.text)
    hidden = [
        e for e in _in_text(_undisguised(page.text)) if e not in plain and own_address(e, site)
    ]
    found = [e for e in (m.lower() for m in [*mailtos, *plain, *hidden]) if is_email(e)]
    return _unique(
        [e for e in found if not any(i in e for i in _IGNORED) and not e.endswith(_IMAGE)]
    )


def _phones(page: Page, country: str) -> tuple[str, ...]:
    tel_links = [link[4:] for link in page.links if link.lower().startswith("tel:")]
    tels = " ".join(tel_links[:MAX_TEL_LINKS])
    numbers = []
    for match in phonenumbers.PhoneNumberMatcher(f"{page.text[:20_000]} {tels}", country):
        if phonenumbers.is_valid_number(match.number):
            numbers.append(
                phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
            )
    return _unique(numbers)


def _company_page(link: str) -> bool:
    parts = urlsplit(link)
    host, path = (parts.hostname or "").lower(), parts.path.lower()
    return any(
        (host == domain or host.endswith("." + domain)) and path.startswith(start)
        and len(path.strip("/")) > len(start.strip("/")) and not path.startswith(refused)
        for domain, start, refused in _SOCIAL
    )  # fmt: skip


def find_contacts(page: Page, country: str, site: str = "") -> Contacts:
    """`site` : adresse du site lu ; une adresse déguisée n'est gardée que sur son domaine ou
    chez une messagerie grand public (C187)."""
    social = [link for link in page.links if _company_page(link) and web_link(link)]
    return Contacts(_emails(page, site), _phones(page, country or "FR"), _unique(social))


def merge_contacts(found: list[Contacts]) -> Contacts:
    """Contacts de plusieurs pages du même site (accueil, puis page Contact), sans doublon."""
    return Contacts(*(_unique([x for c in found for x in getattr(c, k)])
                      for k in ("emails", "phones", "social")))  # fmt: skip
