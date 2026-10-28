"""Cellule de tableur sûre (C89, règle 5) : un texte venu d'un site ou d'une API ne devient
jamais une formule dans Excel ou LibreOffice (=, +, -, @, tabulation, retour chariot)."""

import re

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")
MAX_CELL = 32_000  # Excel refuse plus de 32 767 caractères par cellule


def safe_cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        text = _CONTROL.sub(" ", str(value))[:MAX_CELL]
        return f"'{text}" if text.startswith(_FORMULA_START) else text
    return value
