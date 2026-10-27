"""Page d'un site, lue avec la bibliothèque standard (pas de dépendance en plus).

Seul ce qui sert à l'audit est gardé, en quantité bornée. Le HTML n'est jamais exécuté ni
réaffiché : les textes repris sont neutralisés à l'affichage (règle 5).
"""

from dataclasses import dataclass
from html.parser import HTMLParser

MAX_ITEMS = 300
MAX_TEXT = 100_000
MAX_TITLE = 300
_HIDDEN = {"script", "style", "noscript", "template", "svg"}


@dataclass(frozen=True)
class Page:
    raw: str  # HTML brut (signatures de technologie, année du copyright)
    title: str
    metas: dict[str, str]  # nom (en minuscules) → contenu
    h1: tuple[str, ...]
    forms: int
    email_inputs: int
    links: tuple[str, ...]
    image_alts: tuple[str, ...]
    sources: tuple[str, ...]  # adresses des scripts, images et feuilles de style
    text: str


class _Reader(HTMLParser):
    """Un seul passage, coût constant par balise : compteurs de profondeur, pas de pile."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title, self.forms, self.email_inputs, self.size = "", 0, 0, 0
        self.metas: dict[str, str] = {}
        self.h1: list[str] = []
        self.links: list[str] = []
        self.alts: list[str] = []
        self.sources: list[str] = []
        self.words: list[str] = []
        self.depth = dict.fromkeys((*_HIDDEN, "title", "h1"), 0)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): v or "" for k, v in attrs}
        if tag in self.depth:
            self.depth[tag] += 1
        if tag == "meta" and a.get("name") and len(self.metas) < MAX_ITEMS:
            self.metas.setdefault(a["name"].lower(), a.get("content", "")[:500])
        elif tag == "form":
            self.forms += 1
        elif tag == "input" and a.get("type", "").lower() == "email":
            self.email_inputs += 1
        elif tag == "a" and a.get("href") and len(self.links) < MAX_ITEMS:
            self.links.append(a["href"][:500])
        if tag == "img" and a.get("alt") and len(self.alts) < MAX_ITEMS:
            self.alts.append(a["alt"][:300])
        src = a.get("src") or (a.get("href") if tag == "link" else "")
        if src and len(self.sources) < MAX_ITEMS:
            self.sources.append(src[:500])

    def handle_endtag(self, tag: str) -> None:
        if self.depth.get(tag):
            self.depth[tag] -= 1

    def handle_data(self, data: str) -> None:
        if any(self.depth[t] for t in _HIDDEN):
            return
        if self.depth["title"]:
            self.title = (self.title + data)[:MAX_TITLE]
            return
        if self.depth["h1"] and len(self.h1) < MAX_ITEMS:
            self.h1.append(data[:300])
        if self.size < MAX_TEXT:
            self.words.append(data[: MAX_TEXT - self.size])
            self.size += len(self.words[-1])


def parse_page(html: str) -> Page:
    reader = _Reader()
    reader.feed(html)
    reader.close()
    text = " ".join(" ".join(reader.words).split())[:MAX_TEXT]
    h1 = tuple(t for t in (" ".join(h.split()) for h in reader.h1) if t)
    return Page(
        html, " ".join(reader.title.split())[:MAX_TITLE], reader.metas, h1, reader.forms,
        reader.email_inputs, tuple(reader.links), tuple(reader.alts), tuple(reader.sources), text,
    )  # fmt: skip
