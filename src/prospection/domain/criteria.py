"""Critères de qualification d'un établissement (C19 à C23, C30)."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Criteria:
    min_reviews: int | None = None
    max_reviews: int | None = 30
    website: Literal["any", "with", "without"] = "any"
    phone: Literal["any", "with", "mobile"] = "with"
    exclude_franchises: bool = True
