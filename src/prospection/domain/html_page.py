"""Page d'un site, lue avec la bibliothèque standard (pas de dépendance en plus).

Seul ce qui sert à l'audit est gardé, en quantité bornée. Le HTML n'est jamais exécuté ni
réaffiché : les textes repris sont neutralisés à l'affichage (règle 5).
"""

from dataclasses import dataclass, field
from html.parser import HTMLParser

from prospection.domain.form_fields import field_kind

MAX_ITEMS = 300
MAX_TEXT = 100_000
MAX_TITLE = 300
MAX_CLASSES = 2000
_HIDDEN = {"script", "style", "noscript", "template", "svg"}


@dataclass(frozen=True)
class Page:
    raw: str  # HTML brut (signatures de technologie, année du copyright)
    title: str
    metas: dict[str, str]  # nom (en minuscules) → contenu
    h1: tuple[str, ...]
    forms: int  # formulaires de contact : un champ email ou message, ni recherche ni connexion
    email_inputs: int  # champs email ou message hors formulaire (construits en JavaScript)
    h1_count: int
    images: int
    links: tuple[str, ...]
    image_alts: tuple[str, ...]
    sources: tuple[str, ...]  # adresses des scripts, images et feuilles de style
    text: str
    form_at: float | None = None  # part du texte avant le premier formulaire de contact (0 à 1)
    truncated: bool = False  # page coupée à la lecture : la fin n'a pas été vue
    anchors: tuple[tuple[str, str], ...] = ()  # liens : (adresse, texte affiché)
    classes: dict[str, float] = field(default_factory=dict)  # classe CSS → position (0 à 1)


class _Reader(HTMLParser):
    """Un seul passage, coût constant par balise : compteurs de profondeur, pas de pile."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title, self.forms, self.email_inputs, self.size = "", 0, 0, 0
        self.h1_count = self.images = self.form_start = 0
        self.form: set[str] | None = None  # champs du formulaire en cours
        self.first_form: int | None = None  # position (en caractères) du premier formulaire
        self.anchor: list[str] | None = None  # lien en cours : [adresse, texte]
        self.anchors: list[tuple[str, str]] = []
        self.classes: dict[str, int] = {}  # première position de chaque classe CSS
        self.metas: dict[str, str] = {}
        self.h1: list[str] = []
        self.links: list[str] = []
        self.alts: list[str] = []
        self.sources: list[str] = []
        self.words: list[str] = []
        self.depth = dict.fromkeys((*_HIDDEN, "title", "h1"), 0)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): v or "" for k, v in attrs}
        for name in a.get("class", "").lower().split()[:20]:
            if len(self.classes) < MAX_CLASSES:
                self.classes.setdefault(name[:80], self.size)
        if tag in self.depth:
            self.depth[tag] += 1
        if tag == "meta" and a.get("name") and len(self.metas) < MAX_ITEMS:
            self.metas.setdefault(a["name"].lower(), a.get("content", "")[:500])
        elif tag == "form":
            self.form = {"search"} if a.get("role", "").lower() == "search" else set()
            self.form_start = self.size
        elif tag in ("input", "textarea"):
            self._field(tag, a)
        if tag == "h1":
            self.h1_count += 1
        if tag == "img":
            self.images += 1
        elif tag == "a" and a.get("href") and len(self.links) < MAX_ITEMS:
            self.links.append(a["href"][:500])
            self.anchor = [a["href"][:500], ""]
        if tag == "img" and a.get("alt") and len(self.alts) < MAX_ITEMS:
            self.alts.append(a["alt"][:300])
        src = a.get("src") or (a.get("href") if tag == "link" else "")
        if src and len(self.sources) < MAX_ITEMS:
            self.sources.append(src[:500])

    def _field(self, tag: str, a: dict[str, str]) -> None:
        kind = field_kind(tag, a)
        if self.form is not None:
            self.form.add(kind)
        elif kind in ("email", "textarea"):
            self.email_inputs += 1
            self.first_form = self.size if self.first_form is None else self.first_form

    def end_form(self) -> None:
        if self.form and self.form & {"email", "tel", "textarea"} and not self.form & {
            "password", "search",
        }:  # fmt: skip
            self.forms += 1
            self.first_form = self.form_start if self.first_form is None else self.first_form
        self.form = None

    def handle_endtag(self, tag: str) -> None:
        if self.depth.get(tag):
            self.depth[tag] -= 1
        if tag == "form":
            self.end_form()
        if tag == "a" and self.anchor is not None:
            if len(self.anchors) < MAX_ITEMS:
                self.anchors.append((self.anchor[0], " ".join(self.anchor[1].split())))
            self.anchor = None

    def handle_data(self, data: str) -> None:
        if any(self.depth[t] for t in _HIDDEN):
            return
        if self.depth["title"]:
            self.title = (self.title + data)[:MAX_TITLE]
            return
        if self.anchor is not None and len(self.anchor[1]) < MAX_TITLE:
            self.anchor[1] += " " + data[:MAX_TITLE]
        if self.depth["h1"] and len(self.h1) < MAX_ITEMS:
            self.h1.append(data[:300])
        if self.size < MAX_TEXT:
            self.words.append(data[: MAX_TEXT - self.size])
            self.size += len(self.words[-1])


def parse_page(html: str, truncated: bool = False) -> Page:
    """`truncated` : la lecture s'est arrêtée avant la fin de la page (taille maximale)."""
    reader = _Reader()
    reader.feed(html)
    reader.close()
    reader.end_form()  # formulaire resté ouvert (page coupée) : il compte quand même
    total = max(reader.size, 1)
    at = None if reader.first_form is None else reader.first_form / total
    classes = {name: where / total for name, where in reader.classes.items()}
    text = " ".join(" ".join(reader.words).split())[:MAX_TEXT]
    h1 = tuple(t for t in (" ".join(h.split()) for h in reader.h1) if t)
    return Page(
        html, " ".join(reader.title.split())[:MAX_TITLE], reader.metas, h1, reader.forms,
        reader.email_inputs, reader.h1_count, reader.images, tuple(reader.links),
        tuple(reader.alts), tuple(reader.sources), text, at, truncated, tuple(reader.anchors),
        classes,
    )  # fmt: skip
