"""Texte saisi : sans caractères de contrôle (un NUL fait échouer la base)."""

import re

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_LINE_BREAKS = re.compile(r"[\t\n]")


def without_controls(text: str, keep_lines: bool = False) -> str:
    """Retire les caractères de contrôle ; garde les sauts de ligne si `keep_lines`."""
    clean = _CONTROL.sub("", text)
    return clean if keep_lines else _LINE_BREAKS.sub(" ", clean)
