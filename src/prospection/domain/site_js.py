"""Site affiché seulement par JavaScript (Base44, Lovable, Bolt…) (C152).

La page envoyée est une coquille vide ; texte, liens et formulaire n'apparaissent que dans le
navigateur. L'app ne lance pas de navigateur : elle ne juge pas ce qu'elle ne voit pas.
"""

import re

from prospection.domain.html_page import Page
from prospection.domain.site_findings import MAJOR, Finding
from prospection.domain.site_signals import signals

MAX_WORDS = 20  # au-delà, la page a un vrai contenu lisible
# Ce qui ne se juge pas sur une coquille vide (texte, liens, formulaire, numéro…)
BLIND = frozenset({
    "no_form", "form_contact_only", "thin_content", "no_h1", "no_social", "outdated",
    "no_legal_notice", "no_privacy_policy", "phone_not_clickable", "no_booking",
    "form_buried", "no_cta_top", "form_too_long", "form_no_consent", "quote_incomplete",
})  # fmt: skip
JS_ONLY: Finding = (
    "js_only",
    "Contenu affiché seulement par JavaScript : mal lu par Google, à vérifier à la main",
    MAJOR,
)


def is_js_app(page: Page) -> bool:
    """Coquille : script chargé, racine de l'application vide, presque aucun texte."""
    scripted = any(src.lower().split("?")[0].endswith((".js", ".mjs")) for src in page.sources)
    ids = "|".join(re.escape(i) for i in signals().js_app_roots)
    empty_root = re.search(rf"""id=["']({ids})["'][^>]*>\s*</""", page.raw, re.IGNORECASE)
    return scripted and empty_root is not None and len(page.text.split()) < MAX_WORDS
