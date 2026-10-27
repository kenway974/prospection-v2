"""Retrouver le site d'une entreprise absent de sa fiche Google (C46, C47).

Quelques domaines sont devinés à partir du nom ; un domaine n'est adopté que si sa page
confirme l'entreprise (même téléphone, ou nom complet et code postal ou ville). Le nom seul
ne suffit jamais : c'est peut-être un homonyme, signalé « à confirmer » et pas adopté.

Repris de prospection-bot (services/site_finder.py : candidate_domains, page_confirms,
version 530ba12), amélioré : pas de devinette pour un nom générique (« Plomberie Reims »),
domaine du pays de l'établissement plutôt que toujours .lu/.be/.ch, nom d'un seul mot
confirmé par le téléphone seulement.
"""

import re
from typing import Literal

from prospection.domain.company import LEGAL_WORDS, LINK_WORDS, postal_code
from prospection.domain.trades import find_trade, load_trades, normalize

Confirmation = Literal["fort", "faible"]
STRONG: Confirmation = "fort"
WEAK: Confirmation = "faible"
_COUNTRY_TLD = {"BE": "be", "CH": "ch", "LU": "lu", "MC": "mc"}


def _tokens(name: str) -> list[str]:
    return [t for t in normalize(name).split() if t not in LEGAL_WORDS | LINK_WORDS]


def _full(name: str) -> list[str]:
    """Le nom sans la forme juridique, mots de liaison gardés (« boulangerie de la gare »)."""
    return [t for t in normalize(name).split() if t not in LEGAL_WORDS]


def _generic(keywords: tuple[str, ...], city: str | None) -> set[str]:
    words = set(normalize(city or "").split())
    trades = load_trades()
    for keyword in keywords:
        words |= set(normalize(keyword).split())
        trade = find_trade(keyword, trades)
        if trade:
            words |= {
                w for term in (*trade.aliases, *trade.name_words) for w in normalize(term).split()
            }
    return words


def address_city(address: str) -> str | None:
    """Ville d'une adresse Google (« 12 rue X, 51100 Reims, France » → « Reims »)."""
    postal = postal_code(address)
    if not postal:
        return None
    city = address.split(postal, 1)[1].split(",")[0].strip()
    return city or None


def candidate_domains(
    name: str, country: str | None, keywords: tuple[str, ...], city: str | None
) -> list[str]:
    """Domaines plausibles, du plus probable au moins probable ; aucun si le nom est générique."""
    tokens = _tokens(name)
    if not tokens or not set(tokens) - _generic(keywords, city):
        return []
    joined, dashed = "".join(tokens), "-".join(tokens)
    if not 3 <= len(joined) <= 40:
        return []
    slugs = list(dict.fromkeys((joined, dashed, "".join(_full(name)))))
    tlds = [_COUNTRY_TLD.get(country or "FR", "fr"), "com"]
    return [f"{slug}.{tld}" for tld in dict.fromkeys(tlds) for slug in slugs]


def _last9(number: str | None) -> str:
    return re.sub(r"\D", "", number or "")[-9:]


def confirmation(
    text: str, name: str, phone: str | None, address: str, page_phones: tuple[str, ...] = ()
) -> Confirmation | None:
    """La page parle-t-elle bien de cette entreprise ? `page_phones` : numéros lus sur la page
    (jamais des chiffres épars mis bout à bout, qui formeraient un faux numéro)."""
    wanted = _last9(phone)
    if len(wanted) == 9 and any(_last9(p) == wanted for p in page_phones):
        return STRONG
    tokens = _tokens(name)
    page = f" {normalize(text)} "
    phrases = {" ".join(tokens), " ".join(_full(name))}
    if not tokens or not any(f" {phrase} " in page for phrase in phrases):
        return None
    postal, city = postal_code(address), normalize(address_city(address) or "")
    local = (postal and f" {postal} " in page) or (city and f" {city} " in page)
    return STRONG if local and len(tokens) >= 2 else WEAK
