"""Genre d'un champ de formulaire (email, téléphone, message…), même mal typé (C137), et
champs propres au métier, qui font un formulaire de devis détaillé (C153), et résumé de
chaque formulaire lu (C159)."""

from dataclasses import dataclass

# Champ texte reconnu par son nom (thèmes qui n'écrivent pas type="email") : indice → genre
_HINTS = (("mail", "email"), ("phone", "tel"), ("tel", "tel"), ("portable", "tel"),
          ("message", "textarea"))  # fmt: skip
_NAMING = ("name", "id", "placeholder", "autocomplete", "aria-label")


# Champs qui posent une question sur le besoin (liste de choix, photos, date, nombre…)
_TRADE_KINDS = frozenset({"select", "file", "date", "number", "radio", "range", "datetime-local",
                          "month", "week", "time"})  # fmt: skip
_TRADE_WORDS = ("surface", "superficie", "travaux", "prestation", "service", "projet", "budget",
                "adresse", "postal", "ville", "commune", "date", "delai", "délai", "photo",
                "metrage", "métrage", "m2", "m²", "dimension", "quantit", "modele", "modèle",
                "vehicule", "véhicule", "piece", "pièce", "intervention", "besoin", "chantier",
                "type")  # fmt: skip


def field_kind(tag: str, a: dict[str, str]) -> str:
    if tag in ("textarea", "select"):
        return tag
    kind = a.get("type", "text").lower() or "text"
    if kind != "text":
        return kind
    words = " ".join(a.get(k, "") for k in _NAMING).lower()
    return next((genre for hint, genre in _HINTS if hint in words), kind)


def trade_field(kind: str, a: dict[str, str]) -> bool:
    """Le champ pose une question sur le besoin du client (pas nom, email, message, accord)."""
    if kind in _TRADE_KINDS:
        return True
    if kind in ("checkbox", "hidden", "submit", "button", "email", "tel", "password"):
        return False
    words = " ".join(a.get(k, "") for k in _NAMING).lower()
    return any(w in words for w in _TRADE_WORDS)


_CONSENT_WORDS = ("rgpd", "gdpr", "consent", "accept", "confidentialit", "donnees", "données",
                  "privacy", "vie privée", "vie-privee")  # fmt: skip
_CONTACT_KINDS = frozenset({"email", "tel", "textarea"})
_SKIPPED = frozenset({"checkbox", "hidden", "submit", "button", "reset", "image"})
MAX_LABELS, MAX_FORM_TEXT = 40, 2000


@dataclass(frozen=True)
class FormSummary:
    """Ce qu'un formulaire de contact demande (C153, C159)."""

    trade_fields: int  # questions sur le besoin
    required: int  # champs obligatoires (hors case d'accord)
    consent: bool  # case d'accord ou mention des données personnelles
    words: str  # noms, indications et textes du formulaire, en minuscules (questions posées)


class FormState:
    """Formulaire en cours de lecture."""

    def __init__(self, search: bool) -> None:
        self.kinds: set[str] = {"search"} if search else set()
        self.trade = self.required = 0
        self.consent = False
        self.labels: list[str] = []
        self.text = ""

    def field(self, tag: str, a: dict[str, str]) -> None:
        kind = field_kind(tag, a)
        self.kinds.add(kind)
        self.trade += trade_field(kind, a)
        naming = " ".join(a.get(k, "") for k in _NAMING).lower()
        self.required += "required" in a and kind not in _SKIPPED
        self.consent |= kind == "checkbox" and any(w in naming for w in _CONSENT_WORDS)
        if len(self.labels) < MAX_LABELS:
            self.labels.append(f"{kind} {naming}"[:120])

    def data(self, text: str) -> None:
        if len(self.text) < MAX_FORM_TEXT:
            self.text = (self.text + " " + text)[:MAX_FORM_TEXT]

    def is_contact(self) -> bool:
        return bool(self.kinds & _CONTACT_KINDS) and not self.kinds & {"password", "search"}

    def summary(self) -> FormSummary:
        words = " ".join((*self.labels, self.text.lower()))
        consent = self.consent or any(w in self.text.lower() for w in _CONSENT_WORDS)
        return FormSummary(self.trade, self.required, consent, " ".join(words.split()))
