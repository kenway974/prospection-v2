"""Chercher une adresse email au-delà de l'accueil (C188).

Sans email sur les pages déjà lues, la page Contact (même si l'accueil a un formulaire) et
la page « Mentions légales » sont lues, dans le temps qui reste aux pages en plus du site :
un prospect « sans email » ne peut pas recevoir le mail d'audit. Seules les adresses du site
ou d'une messagerie grand public sont gardées : jamais l'hébergeur ni l'agence web.
"""

from collections.abc import Callable, Sequence
from time import monotonic

from prospection.domain.email_owner import own_address, same_site
from prospection.domain.html_page import Page, parse_page
from prospection.domain.site_contacts import Contacts, find_contacts, merge_contacts
from prospection.domain.site_form import contact_links, has_form, legal_links
from prospection.sources.web_reader import ReadResult

Reader = Callable[[str, float], ReadResult]  # adresse, secondes au plus → page lue (C166)
MIN_READ_SECONDS = 1.0


def _targets(home: Page, url: str) -> list[str]:
    contact = contact_links(home, url)
    if not has_form(home):  # les pages Contact ont déjà été lues (C138)
        return [link for link in legal_links(home, url) if link not in contact]
    return list(dict.fromkeys([*contact, *legal_links(home, url)]))


def _emails_at(read: Reader, link: str, url: str, left: float, country: str) -> tuple[str, ...]:
    result = read(link, left)
    if result.page is None or not same_site(result.page.url, url):  # redirigée ailleurs
        return ()
    page = parse_page(result.page.html, result.page.truncated)
    return tuple(e for e in find_contacts(page, country, url).emails if own_address(e, url))


def site_contacts(
    read: Reader, home: Page, others: Sequence[Page], url: str, country: str, deadline: float
) -> Contacts:
    """`deadline` (horloge monotone) : fin du temps commun à toutes les pages en plus."""
    found = merge_contacts([find_contacts(p, country, url) for p in (home, *others)])
    if found.emails:
        return found
    for link in _targets(home, url):
        left = deadline - monotonic()
        if left < MIN_READ_SECONDS:
            break
        if emails := _emails_at(read, link, url, left, country):
            return merge_contacts([found, Contacts(emails, (), ())])
    return found
