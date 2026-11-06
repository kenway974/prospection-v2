"""Genre d'un champ de formulaire (email, téléphone, message…), même mal typé (C137), et
champs propres au métier, qui font un formulaire de devis détaillé (C153)."""

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
