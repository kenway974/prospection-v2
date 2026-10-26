"""Franchises et chaînes (C30), sans exclure les indépendants au nom proche (C31).

Liste dans `data/franchises.yaml`, reprise de prospection-bot/services/franchises.py
(530ba12) : `national` = exclu si le nom contient l'enseigne (mot entier) ;
`ambiguous` = exclu seulement si le nom EST l'enseigne, sinon « à vérifier ».
"""

import re
from collections.abc import Iterable
from functools import cache
from importlib import resources
from typing import Literal

import yaml
from pydantic import BaseModel

from prospection.domain.trades import normalize

BrandMatch = tuple[Literal["exclude", "check"], str]


class _Brands(BaseModel):
    national: tuple[str, ...]
    ambiguous: tuple[str, ...]


@cache
def _brands() -> _Brands:
    text = resources.files("prospection.data").joinpath("franchises.yaml").read_text("utf-8")
    return _Brands.model_validate(yaml.safe_load(text))


def _contains_word(haystack: str, needle: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
    return bool(needle) and re.search(pattern, haystack) is not None


def brand_match(name: str, personal: Iterable[str]) -> BrandMatch | None:
    """Enseigne reconnue dans le nom : à exclure, à vérifier, ou rien."""
    norm = normalize(name)
    if not norm:
        return None
    brands = _brands()
    for brand in (*brands.national, *personal):
        if _contains_word(norm, normalize(brand)):
            return "exclude", normalize(brand)
    for brand in brands.ambiguous:
        if norm == normalize(brand):
            return "exclude", normalize(brand)
    for brand in brands.ambiguous:
        if _contains_word(norm, normalize(brand)):
            return "check", normalize(brand)
    return None
