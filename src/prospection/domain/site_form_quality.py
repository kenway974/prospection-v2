"""Qualité du formulaire de contact (C158, C159, C167) : enterré en bas de la page Contact,
sans bouton d'action en haut de l'accueil, trop long, sans mention RGPD, sans les questions
d'une première estimation pour le métier."""

import re
from collections.abc import Sequence

from prospection.domain.form_fields import FormSummary
from prospection.domain.html_page import Page
from prospection.domain.site_findings import MINOR, Finding
from prospection.domain.site_form import CONTACT_PAGE, HOME, MIN_TRADE_FIELDS, TOP_SHARE
from prospection.domain.site_signals import signals
from prospection.domain.trades import normalize

_EMAIL_ADDRESS = re.compile(r"adresse (?:e-?mail|mail|électronique|electronique|courriel)")
_PRIVACY = re.compile(r"données personnelles|donnees personnelles|politique de confidentialité")
BURIED_SHARE = 0.5  # plus de la moitié du texte de la page Contact avant le formulaire
MAX_REQUIRED, MAX_LISTED, MIN_MISSING = 6, 3, 2


def best_form(pages: Sequence[Page]) -> FormSummary | None:
    found = [p.best_form for p in pages if p.best_form]
    return max(found, key=lambda f: f.trade_fields) if found else None


def expectation_for(keywords: Sequence[str]) -> str | None:
    """Groupe de métier dont on attend les questions : le premier qui correspond (C167)."""
    words = " ".join(normalize(k) for k in keywords)
    return next(
        (name for name, group in signals().form_expectations.items()
         if any(re.search(rf"\b{re.escape(normalize(m))}", words) for m in group.mots)),
        None,
    )  # fmt: skip


def missing_questions(
    form: FormSummary, keywords: Sequence[str], limit: int = MAX_LISTED
) -> list[str]:
    """Questions attendues pour ce métier que le formulaire ne pose pas (C159, C167).
    « Adresse e-mail » ne répond pas à « adresse » ; le texte d'accord est ignoré."""
    name = expectation_for(keywords)
    if name is None:
        return []
    words = _EMAIL_ADDRESS.sub(" ", _PRIVACY.sub(" ", form.words))
    return [q for q, hints in signals().form_expectations[name].champs.items()
            if not any(h in words for h in hints)][:limit]  # fmt: skip


def _cta_on_top(home: Page) -> bool:
    words = signals().cta_words
    return any(
        at < TOP_SHARE and any(w in f"{href} {label}".lower() for w in words)
        for (href, label), at in zip(home.anchors, home.anchors_at, strict=False)
    )


def _incomplete(form: FormSummary, keywords: Sequence[str]) -> list[Finding]:
    """C167 : formulaire de devis qui oublie au moins deux questions d'estimation du métier
    (un formulaire basique est déjà signalé comme tel)."""
    missing = missing_questions(form, keywords)
    if form.trade_fields < MIN_TRADE_FIELDS or len(missing) < MIN_MISSING:
        return []
    text = f"Formulaire de demande incomplet : il manque {', '.join(missing)}"
    return [("quote_incomplete", text, MINOR)]


def form_findings(
    home: Page, others: Sequence[Page], place: str, keywords: Sequence[str] = ()
) -> list[Finding]:
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
    return found + (_incomplete(form, keywords) if form else [])
