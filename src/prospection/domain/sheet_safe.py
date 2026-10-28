"""Cellule de tableur sûre (C89, règle 5) : un texte venu d'un site ou d'une API ne devient
jamais une formule dans Excel ou LibreOffice (=, +, -, @, tabulation, retour chariot)."""

import re

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Formule possible : =, +, -, @ (et leurs variantes pleine largeur), même après des espaces
_FORMULA_START = ("=", "+", "-", "@", "\uff1d", "\uff0b", "\uff0d", "\uff20")
MAX_CELL = 32_000  # Excel refuse plus de 32 767 caractères par cellule


def safe_cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        text = _CONTROL.sub(" ", str(value))[:MAX_CELL]
        risky = text[:1] in ("\t", "\r", "\n") or text.lstrip().startswith(_FORMULA_START)
        return f"'{text}" if risky else text
    return value
