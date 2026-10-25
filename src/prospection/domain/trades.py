"""Métiers reconnus et synonymes à chercher (C12, C15).

Les métiers vivent dans le fichier de données `data/trades.yaml` (validé au
chargement). Source des métiers du bâtiment : prospection-bot/trades.py (530ba12).
"""

import re
import unicodedata
from collections.abc import Iterable, Sequence
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_QUERIES_PER_KEYWORD = 3


class InvalidTradeFile(ValueError):
    """Le fichier des métiers est mal formé."""


class Trade(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    label: str
    aliases: tuple[str, ...] = Field(min_length=1)
    queries: tuple[str, ...]
    name_words: tuple[str, ...]
    maps_types: frozenset[str]
    naf_prefixes: tuple[str, ...]
    family: Literal["batiment", "commerce"]
    off_target_name_words: tuple[str, ...] = ()


def normalize(text: str) -> str:
    """Minuscules, sans accents ni ponctuation : « Électricité » → « electricite »."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def _singular(text: str) -> str:
    return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") else w for w in text.split())


def _key(text: str) -> str:
    return _singular(normalize(text))


def load_trades(path: Path | None = None) -> tuple[Trade, ...]:
    if path is None:
        text = resources.files("prospection.data").joinpath("trades.yaml").read_text("utf-8")
    else:
        text = path.read_text("utf-8")
    try:
        entries = yaml.safe_load(text)
        return tuple(Trade.model_validate(entry) for entry in entries)
    except (yaml.YAMLError, ValidationError, TypeError) as error:
        raise InvalidTradeFile(f"Fichier des métiers invalide : {error}") from None


def find_trade(keyword: str, trades: Sequence[Trade]) -> Trade | None:
    """Métier correspondant à un mot-clé saisi (pluriel et accents tolérés), ou None."""
    wanted = _key(keyword)
    if not wanted:
        return None
    return next((t for t in trades if any(wanted == _key(a) for a in t.aliases)), None)


def expand_queries(
    keywords: Iterable[str], trades: Sequence[Trade], synonyms_on: bool
) -> list[str]:
    """Requêtes à lancer : chaque mot-clé saisi, puis ses synonymes (sans doublon)."""
    queries: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        trade = find_trade(keyword, trades) if synonyms_on else None
        candidates = [keyword, *(trade.queries if trade else ())][:MAX_QUERIES_PER_KEYWORD]
        for query in candidates:
            if _key(query) not in seen:
                seen.add(_key(query))
                queries.append(query)
    return queries
