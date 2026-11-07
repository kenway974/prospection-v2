"""Qualité du formulaire de contact (C158, C159) : enterré en bas de la page Contact, sans
bouton d'action en haut de l'accueil, trop long, sans mention RGPD, sans les questions utiles
au métier."""

import re
from collections.abc import Sequence

from prospection.domain.form_fields import FormSummary
from prospection.domain.html_page import Page
from prospection.domain.site_findings import MINOR, Finding
from prospection.domain.site_form import CONTACT_PAGE, HOME, TOP_SHARE
from prospection.domain.site_signals import signals
from prospection.domain.trades import normalize

BURIED_SHARE = 0.5  # plus de la moitié du texte de la page Contact avant le formulaire
MAX_REQUIRED, MAX_LISTED = 6, 3


def best_form(pages: Sequence[Page]) -> FormSummary | None:
    found = [p.best_form for p in pages if p.best_form]
    return max(found, key=lambda f: f.trade_fields) if found else None


def missing_questions(form: FormSummary, keywords: Sequence[str]) -> list[str]:
    """Questions attendues pour ce métier que le formulaire ne pose pas (C159)."""
    words = " ".join(normalize(k) for k in keywords)
    for group in signals().form_expectations.values():
        if any(re.search(rf"\b{re.escape(normalize(m))}", words) for m in group.mots):
            return [q for q, hints in group.champs.items()
                    if not any(h in form.words for h in hints)][:MAX_LISTED]  # fmt: skip
    return []


def _cta_on_top(home: Page) -> bool:
    words = signals().cta_words
    return any(
        at < TOP_SHARE and any(w in f"{href} {label}".lower() for w in words)
        for (href, label), at in zip(home.anchors, home.anchors_at, strict=False)
    )


def form_findings(home: Page, others: Sequence[Page], place: str) -> list[Finding]:
    found: list[Finding] = []
    contact = [p for p in others if p.forms > 0]
    if place == CONTACT_PAGE and contact and (contact[0].form_at or 0) > BURIED_SHARE:
        found.append(("form_buried", "Formulaire tout en bas de la page Contact", MINOR))
    if place in (HOME, CONTACT_PAGE) and not _cta_on_top(home):
        text = "Pas de bouton « Devis » ou « Rendez-vous » visible en haut de l'accueil"
        found.append(("no_cta_top", text, MINOR))
    form = best_form([home, *others])
    if form and form.required > MAX_REQUIRED:
        text = f"Formulaire trop long : {form.required} champs obligatoires"
        found.append(("form_too_long", text, MINOR))
    if form and not form.consent:
        text = "Formulaire sans mention RGPD (accord ou lien vers la confidentialité)"
        found.append(("form_no_consent", text, MINOR))
    return found
