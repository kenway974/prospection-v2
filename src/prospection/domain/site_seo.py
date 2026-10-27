"""SEO local : le métier et la ville apparaissent-ils là où Google regarde ? (C51)"""

from dataclasses import dataclass

from prospection.domain.html_page import Page
from prospection.domain.trades import comparable, find_trade, load_trades

PLACES = ("titre", "h1", "texte", "images")


@dataclass(frozen=True)
class LocalSeo:
    trade: dict[str, bool]  # emplacement → métier présent
    city: dict[str, bool]
    problems: tuple[str, ...]


def _words(text: str) -> str:
    """Texte comparable (sans accents, au singulier), bordé d'espaces."""
    return f" {comparable(text)} "


def _terms(keywords: tuple[str, ...]) -> set[str]:
    trades = load_trades()
    terms = set(keywords)
    for keyword in keywords:
        trade = find_trade(keyword, trades)
        if trade:
            terms |= {trade.label, *trade.aliases, *trade.name_words}
    return {t for t in (_words(term) for term in terms) if t.strip()}


def _found(page: Page, terms: set[str]) -> dict[str, bool]:
    sections = (page.title, " ".join(page.h1), page.text, " ".join(page.image_alts))
    texts = [_words(s) for s in sections]
    return {place: any(t in text for t in terms) for place, text in zip(PLACES, texts, strict=True)}


def local_seo(page: Page, keywords: tuple[str, ...], city: str | None) -> LocalSeo:
    trade = _found(page, _terms(keywords))
    town = _found(page, {_words(city)} if city and city.strip() else set())
    problems = []
    if not (trade["titre"] or trade["h1"]):
        problems.append("Le métier n'apparaît ni dans le titre ni dans le H1")
    if city and not (town["titre"] or town["h1"]):
        problems.append("La ville n'apparaît ni dans le titre ni dans le H1")
    return LocalSeo(trade, town, tuple(problems))
