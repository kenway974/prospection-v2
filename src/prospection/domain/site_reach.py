"""Audit « joindre l'entreprise » : numéro cliquable, réservation en ligne (C142)."""

import re
from collections.abc import Sequence

from prospection.domain.html_page import Page
from prospection.domain.site_findings import MAJOR, MINOR, Finding
from prospection.domain.site_signals import signals
from prospection.domain.trades import normalize


def needs_booking(keywords: Sequence[str]) -> bool:
    """Métier où les clients réservent (restauration, beauté, santé, sport…)."""
    words = " ".join(normalize(k) for k in keywords)
    return any(re.search(rf"\b{re.escape(t)}", words) for t in signals().booking_trades)


def _books_online(page: Page) -> bool:
    s = signals()
    haystack = " ".join((*page.links, *page.sources)).lower()
    labels = " ".join(label for _, label in page.anchors).lower()
    return any(b in haystack for b in s.booking_services) or any(
        w in labels or w in haystack for w in s.booking_words
    )


def reach_findings(page: Page, phones: Sequence[str], keywords: Sequence[str]) -> list[Finding]:
    """`phones` : numéros lus sur la page ; `keywords` : métiers recherchés."""
    clickable = any(link.lower().startswith("tel:") for link in page.links)
    checks = [
        (bool(phones) and not clickable, "phone_not_clickable",
         "Numéro affiché mais pas cliquable sur téléphone", MINOR),
        (needs_booking(keywords) and not _books_online(page), "no_booking",
         "Pas de réservation en ligne", MAJOR),
    ]  # fmt: skip
    return [(code, text, weight) for failed, code, text, weight in checks if failed]
