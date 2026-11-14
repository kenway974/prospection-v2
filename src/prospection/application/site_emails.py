"""Chercher une adresse email au-delà de l'accueil (C188).

Sans email sur les pages déjà lues, la page Contact (même si l'accueil a un formulaire) et
la page « Mentions légales » sont lues, dans un temps limité : un prospect « sans email »
ne peut pas recevoir le mail d'audit.
"""

from collections.abc import Callable, Sequence
from time import monotonic

from prospection.domain.html_page import Page, parse_page
from prospection.domain.site_contacts import Contacts, find_contacts, merge_contacts
from prospection.domain.site_form import contact_links, has_form, legal_links
from prospection.sources.web_reader import ReadResult

Reader = Callable[[str, float], ReadResult]  # adresse, secondes au plus → page lue (C166)
EMAIL_SECONDS = 6.0  # budget commun des pages lues pour trouver un email
MIN_READ_SECONDS = 1.0


def site_contacts(
    read: Reader, home: Page, others: Sequence[Page], url: str, country: str
) -> Contacts:
    found = merge_contacts([find_contacts(p, country) for p in (home, *others)])
    if found.emails:
        return found
    # Sans formulaire sur l'accueil, les pages Contact ont déjà été lues (C138)
    targets = [*(contact_links(home, url) if has_form(home) else []), *legal_links(home, url)]
    extra: list[Contacts] = []
    start = monotonic()
    for link in dict.fromkeys(targets):
        left = EMAIL_SECONDS - (monotonic() - start)
        if left < MIN_READ_SECONDS:
            break
        result = read(link, left)
        if result.page is None:
            continue
        extra.append(find_contacts(parse_page(result.page.html, result.page.truncated), country))
        if extra[-1].emails:
            break
    return merge_contacts([found, *extra])
