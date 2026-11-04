"""Genre d'un champ de formulaire (email, téléphone, message…), même mal typé (C137)."""

# Champ texte reconnu par son nom (thèmes qui n'écrivent pas type="email") : indice → genre
_HINTS = (("mail", "email"), ("phone", "tel"), ("tel", "tel"), ("portable", "tel"),
          ("message", "textarea"))  # fmt: skip
_NAMING = ("name", "id", "placeholder", "autocomplete", "aria-label")


def field_kind(tag: str, a: dict[str, str]) -> str:
    if tag == "textarea":
        return "textarea"
    kind = a.get("type", "text").lower() or "text"
    if kind != "text":
        return kind
    words = " ".join(a.get(k, "") for k in _NAMING).lower()
    return next((genre for hint, genre in _HINTS if hint in words), kind)
