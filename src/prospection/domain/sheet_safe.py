"""Cellule de tableur sûre (C89, règle 5) : un texte venu d'un site ou d'une API ne devient
jamais une formule dans Excel ou LibreOffice (=, +, -, @, tabulation, retour chariot)."""

import re

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Formule possible : =, +, -, @ (et leurs variantes pleine largeur), même après des espaces
_FORMULA_START = ("=", "+", "-", "@", "\uff1d", "\uff0b", "\uff0d", "\uff20")
MAX_CELL = 32_000  # Excel refuse plus de 32 767 caractères par cellule


def clean(value: object) -> object:
    """Nombre tel quel ; texte sans caractères de contrôle, borné ; rien → vide."""
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _CONTROL.sub(" ", str(value))[:MAX_CELL]
    return value


def looks_like_formula(text: str) -> bool:
    return text[:1] in ("\t", "\r", "\n") or text.lstrip().startswith(_FORMULA_START)


def safe_cell(value: object) -> object:
    """Pour le CSV : une formule possible est précédée d'une apostrophe (texte pour Excel)."""
    cleaned = clean(value)
    return f"'{cleaned}" if isinstance(cleaned, str) and looks_like_formula(cleaned) else cleaned
