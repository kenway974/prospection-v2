"""Version HTML du mail d'audit, tirée du texte (C145, C146).

Gmail recoupe les mails en texte simple vers 76 caractères : la version HTML garde les
phrases entières. Mise en forme légère : **gras**, lignes « - » en puces. Tout est échappé ;
seuls les liens http(s) deviennent cliquables.
"""

import re
from html import escape

_LINK = re.compile(r"https?://[^\s<>\"']+")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_TRAILING = ".,;:!?)»"
_P = '<p style="margin:0 0 14px">'
_UL = '<ul style="margin:6px 0 18px;padding-left:20px">'


def plain(text: str) -> str:
    """Le texte sans les marques de gras (version texte simple)."""
    return _BOLD.sub(r"\1", text)


def _inline(text: str) -> str:
    parts, last = [], 0
    for found in _LINK.finditer(text):
        url = found.group().rstrip(_TRAILING)
        parts.append(escape(text[last : found.start()]))
        parts.append(f'<a href="{escape(url, quote=True)}">{escape(url)}</a>')
        last = found.start() + len(url)
    parts.append(escape(text[last:]))
    return _BOLD.sub(r"<strong>\1</strong>", "".join(parts))  # après l'échappement


def _block(block: str) -> str:
    lines = [line.strip() for line in block.strip().split("\n")]
    items = [f'<li style="margin:4px 0">{_inline(x[2:])}</li>' for x in lines if x.startswith("- ")]
    others = [_inline(x) for x in lines if not x.startswith("- ")]
    html = f"{_P}{'<br>'.join(others)}</p>" if others else ""
    return html + (f"{_UL}{''.join(items)}</ul>" if items else "")


def to_html(text: str) -> str:
    """Un paragraphe par bloc séparé d'une ligne vide ; ses lignes « - » forment une liste."""
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    body = "".join(_block(b) for b in blocks)
    style = "font-family:Arial,sans-serif;font-size:15px;line-height:1.5;color:#1d1d1f"
    return f'<!doctype html><html><body style="{style}">{body}</body></html>'
