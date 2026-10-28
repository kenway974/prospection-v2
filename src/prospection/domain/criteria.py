"""Critères de qualification d'un établissement (C19 à C23, C28 à C31, C33)."""

from dataclasses import dataclass
from typing import Literal

from prospection.domain.category import category_verdict
from prospection.domain.franchises import brand_match
from prospection.domain.phones import is_mobile
from prospection.domain.place import Place
from prospection.domain.privacy import ERASED_REASON, erasure_key
from prospection.domain.site_guess import address_city
from prospection.domain.trades import Trade, normalize

SiteChoice = Literal["any", "only", "exclude"]


@dataclass(frozen=True)
class Criteria:
    min_reviews: int | None = None
    max_reviews: int | None = 30
    website: Literal["any", "with", "without"] = "any"
    phone: Literal["any", "with", "mobile"] = "with"
    exclude_franchises: bool = True
    created_within_days: int = 90  # source registre : créées depuis au plus N jours (C24)
    max_workforce: str | None = None  # source registre : tranche d'effectif au plus (C26)
    max_site_score: int | None = None  # ne garder que les sites faibles (C28)
    no_form: SiteChoice = "any"  # sites sans formulaire : peu importe, seulement, exclus (C29)
    no_https: SiteChoice = "any"
    not_mobile: SiteChoice = "any"


@dataclass(frozen=True)
class Exclusions:
    personal_franchises: frozenset[str]
    blacklist_ids: frozenset[str]
    blacklist_names: frozenset[str]
    crm_ids: frozenset[str] = frozenset()  # déjà dans le CRM (C32) : ID app, SIREN, nom
    crm_sirens: frozenset[str] = frozenset()
    crm_names: frozenset[str] = frozenset()
    erased: frozenset[str] = frozenset()  # suppression demandée (C95) : empreintes


@dataclass(frozen=True)
class Verdict:
    qualified: bool
    reasons: tuple[str, ...]
    to_check: tuple[str, ...]


def _in_crm_by_name(place: Place, names: frozenset[str]) -> bool:
    """Nom et ville (C32) : un homonyme d'une autre ville n'est pas exclu. Le nom seul ne
    vaut que pour une fiche CRM sans identifiant, sans SIREN et sans ville."""
    name, city = normalize(place.name), normalize(address_city(place.address) or "")
    return f"{name}|{city}" in names or name in names


def _list_reasons(place: Place, criteria: Criteria, exclusions: Exclusions) -> list[str]:
    reasons = []
    if erasure_key(place.place_id) in exclusions.erased:
        reasons.append(ERASED_REASON)
    if place.business_status == "CLOSED_PERMANENTLY":
        reasons.append("Fermé définitivement")
    if place.place_id in exclusions.blacklist_ids or (
        normalize(place.name) in exclusions.blacklist_names
    ):
        reasons.append("Liste noire")
    if place.place_id in exclusions.crm_ids or _in_crm_by_name(place, exclusions.crm_names):
        reasons.append("Déjà dans le CRM")
    return reasons


def _criteria_reasons(place: Place, criteria: Criteria) -> list[str]:
    reasons = []
    count = place.review_count
    if criteria.max_reviews is not None and count > criteria.max_reviews:
        reasons.append(f"Trop d'avis ({count})")
    if criteria.min_reviews is not None and count < criteria.min_reviews:
        reasons.append(f"Pas assez d'avis ({count})")
    if criteria.website == "with" and not place.website:
        reasons.append("Sans site")
    if criteria.website == "without" and place.website:
        reasons.append("Avec site")
    if criteria.phone != "any" and not place.phone:
        reasons.append("Sans téléphone")
    elif criteria.phone == "mobile" and place.phone and not is_mobile(place.phone, place.country):
        reasons.append("Pas de mobile")
    return reasons


def evaluate(
    place: Place, trade: Trade | None, criteria: Criteria, exclusions: Exclusions
) -> Verdict:
    """Raisons d'exclusion (toutes) et points à vérifier ; un établissement sans note
    n'est pas exclu pour ça (C20)."""
    reasons = _list_reasons(place, criteria, exclusions)
    to_check = []
    brand = brand_match(place.name, exclusions.personal_franchises)
    if brand and criteria.exclude_franchises:
        kind, name = brand
        if kind == "exclude":
            reasons.append(f"Franchise ou chaîne ({name})")
        else:
            to_check.append(f"Nom proche de l'enseigne « {name} »")
    if trade is not None:
        verdict, detail = category_verdict(place, trade)
        if verdict == "exclude":
            reasons.append(f"Hors métier ({detail})")
        elif verdict == "check":
            to_check.append(detail)
    reasons.extend(_criteria_reasons(place, criteria))
    return Verdict(not reasons, tuple(reasons), tuple(to_check))
