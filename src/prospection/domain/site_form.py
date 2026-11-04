"""Formulaire de contact : reconnu, cherché sur la page Contact, situé (C137 à C139).

Un formulaire en haut de l'accueil se voit tout de suite ; seul sur une page Contact, un
visiteur pressé ne le trouve pas. Sans certitude (page coupée, constructeur qui dessine ses
formulaires en JavaScript), l'app dit « non vérifié », jamais « aucun ».
"""

from collections.abc import Sequence
from urllib.parse import urljoin, urlsplit

from prospection.domain.html_page import Page
from prospection.domain.site_signals import signals

HOME_TOP, HOME = "en haut de l'accueil", "plus bas sur l'accueil"
CONTACT_PAGE, NONE, UNKNOWN = "sur une page Contact", "aucun", "non vérifié"
FOUND = (HOME_TOP, HOME, CONTACT_PAGE)
TOP_SHARE = 0.25  # moins d'un quart du texte avant le formulaire : visible dès l'arrivée
MAX_PAGES = 2


def _service(page: Page) -> bool:
    return any(s in src.lower() for src in page.sources for s in signals().form_services)


def has_form(page: Page) -> bool:
    return page.forms > 0 or page.email_inputs > 0 or _service(page)


def form_place(home: Page, others: Sequence[Page], technology: str | None) -> str:
    if home.forms > 0 or home.email_inputs > 0:
        at = home.form_at
        return HOME_TOP if at is not None and at < TOP_SHARE else HOME
    if _service(home):
        return HOME
    if any(has_form(p) for p in others):
        return CONTACT_PAGE
    unsure = home.truncated or any(p.truncated for p in others)
    return UNKNOWN if unsure or technology in signals().form_builders else NONE


def _rank(href: str, label: str) -> int | None:
    """Rang du premier mot de contact trouvé dans le chemin ou le texte du lien."""
    words = (urlsplit(href).path + " " + label).lower()
    return next((i for i, w in enumerate(signals().contact_words) if w in words), None)


def contact_links(page: Page, url: str) -> list[str]:
    """Pages du même site qui parlent de contact (les plus utiles d'abord), 2 au plus."""
    host, found = urlsplit(url).hostname, list[tuple[int, int, str]]()
    for href, label in page.anchors:
        target = urljoin(url, href).split("#")[0]
        parts = urlsplit(target)
        if parts.scheme not in ("http", "https") or parts.hostname != host:
            continue
        if target.rstrip("/") == url.split("#")[0].rstrip("/"):
            continue
        if (rank := _rank(target, label)) is not None:
            found.append((rank, len(found), target))
    unique = list(dict.fromkeys(target for _, _, target in sorted(found)))
    return unique[:MAX_PAGES]
