"""Audit RGPD d'un site : mentions légales, confidentialité, consentement aux cookies (C140).

Indices lus dans la page, jamais une certitude juridique : le mail parle de « point à
vérifier ». Matomo et Plausible ne sont pas comptés (exemptables de consentement, CNIL).
"""

from prospection.domain.html_page import Page
from prospection.domain.site_findings import MAJOR, Finding
from prospection.domain.site_signals import signals


def _mentions(page: Page, words: list[str]) -> bool:
    haystack = " ".join((*page.links, *(label for _, label in page.anchors), page.text[-5000:]))
    return any(w in haystack.lower() for w in words)


def tracks_visitors(page: Page) -> bool:
    raw = page.raw.lower()
    return any(t in raw for t in signals().consent_trackers)


def privacy_findings(page: Page, collects: bool) -> list[Finding]:
    """`collects` : le site recueille des données (formulaire de contact)."""
    s, raw = signals(), page.raw.lower()
    tracked = tracks_visitors(page)
    consent = any(tool in raw for tool in s.consent_tools)
    checks = [
        (not _mentions(page, s.legal_words), "no_legal_notice",
         "Pas de mentions légales (obligatoires)", MAJOR),
        ((collects or tracked) and not _mentions(page, s.privacy_words), "no_privacy_policy",
         "Pas de politique de confidentialité alors que le site recueille des données", MAJOR),
        (tracked and not consent, "no_cookie_consent",
         "Traceurs (statistiques, publicité) chargés sans bandeau de consentement", MAJOR),
    ]  # fmt: skip
    return [(code, text, weight) for failed, code, text, weight in checks if failed]
