"""Conditions d'une règle « Pour l'appel » sur les signaux d'un prospect (C110)."""

import operator
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, model_validator

from prospection.domain.page_speed import is_slow
from prospection.domain.signals import Signals
from prospection.domain.site_audit import LEGACY_GA


class Conditions(BaseModel):
    """Toutes les conditions données doivent être vraies ; au moins une est donnée."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    has_site: bool | None = None
    found_site: bool | None = None
    site_score_max: int | None = None
    no_form: bool | None = None
    no_https: bool | None = None
    not_mobile: bool | None = None
    seo_missing: bool | None = None
    reviews_max: int | None = None
    reviews_min: int | None = None
    rating_max: float | None = None
    created_within_days: int | None = None
    no_hours: bool | None = None
    probable_site: bool | None = None  # site du même nom trouvé, homonyme possible
    site_down: bool | None = None  # site de la fiche Google injoignable ou illisible
    slow_site: bool | None = None  # lent sur mobile, mesuré par Google PageSpeed
    dead_analytics: bool | None = None  # ancien Google Analytics, arrêté en 2023

    @model_validator(mode="after")
    def _not_empty(self) -> "Conditions":
        if not self.model_dump(exclude_none=True):
            raise ValueError("une règle a au moins une condition")
        return self


@dataclass(frozen=True)
class _Facts:
    """Signaux utiles aux règles ; None quand ils sont inconnus (site non lu…)."""

    has_site: bool
    found_site: bool
    site_score: int | None
    no_form: bool | None
    no_https: bool | None
    not_mobile: bool | None
    seo_missing: bool | None
    reviews: int
    rating: float | None
    age: int | None
    no_hours: bool
    probable_site: bool
    site_down: bool
    slow_site: bool | None
    dead_analytics: bool | None


def _facts(s: Signals) -> _Facts:
    audit, seo = s.audit, s.site.seo if s.site else None
    return _Facts(
        s.has_site, bool(s.site and s.site.origin == "retrouvé"),
        audit.score if audit else None, (not audit.contact_form) if audit else None,
        (not audit.https) if audit else None, (not audit.mobile) if audit else None,
        bool(seo.problems) if seo else None, s.place.review_count, s.place.rating,
        s.age_days, not s.place.opening_hours, bool(s.site and s.site.probable), s.site_down,
        is_slow(s.site.speed) if s.site and s.site.speed else None,
        (LEGACY_GA in audit.problems) if audit else None,
    )  # fmt: skip


def matches(when: Conditions, s: Signals) -> bool:
    f = _facts(s)
    flags = [(when.has_site, f.has_site), (when.found_site, f.found_site),
             (when.no_form, f.no_form), (when.no_https, f.no_https),
             (when.not_mobile, f.not_mobile), (when.seo_missing, f.seo_missing),
             (when.no_hours, f.no_hours), (when.probable_site, f.probable_site),
             (when.site_down, f.site_down), (when.slow_site, f.slow_site),
             (when.dead_analytics, f.dead_analytics)]  # fmt: skip
    if any(wanted is not None and actual != wanted for wanted, actual in flags):
        return False
    bounds: list[tuple[float | None, float | None, Callable[[float, float], bool]]] = [
        (when.site_score_max, f.site_score, operator.le),
        (when.reviews_max, f.reviews, operator.le),
        (when.reviews_min, f.reviews, operator.ge), (when.rating_max, f.rating, operator.le),
        (when.created_within_days, f.age, operator.le),
    ]  # fmt: skip
    return all(limit is None or (value is not None and compare(value, limit))
               for limit, value, compare in bounds)  # fmt: skip
