"""Version HTML du mail d'audit, tirée du texte (C146).

Gmail recoupe les mails en texte simple vers 76 caractères : la version HTML garde les
phrases entières. Tout est échappé ; seuls les liens http(s) deviennent cliquables.
"""

import re
from html import escape

_LINK = re.compile(r"https?://[^\s<>\"']+")
_TRAILING = ".,;:!?)»"


def _inline(text: str) -> str:
    parts, last = [], 0
    for found in _LINK.finditer(text):
        url = found.group().rstrip(_TRAILING)
        end = found.start() + len(url)
        parts.append(escape(text[last : found.start()]))
        parts.append(f'<a href="{escape(url, quote=True)}">{escape(url)}</a>')
        last = end
    parts.append(escape(text[last:]))
    return "".join(parts)


def to_html(text: str) -> str:
    """Un paragraphe par bloc séparé d'une ligne vide ; un retour à la ligne reste."""
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    paragraphs = (
        "<br>".join(_inline(line.strip()) for line in b.strip().split("\n")) for b in blocks
    )
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    return f'<!doctype html><html><body style="font-family:sans-serif">{body}</body></html>'
