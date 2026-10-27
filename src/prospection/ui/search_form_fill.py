"""Demande de campagne -> formulaire Recherche, pour pré-remplir depuis un modèle (C18)."""

from prospection.domain.campaign_request import (
    CampaignRequest,
    CityZone,
    DepartmentZone,
    RadiusZone,
)
from prospection.domain.criteria import Criteria
from prospection.ui.search_form import commune_value


def _text(number: int | None) -> str:
    return "" if number is None else str(number)


def criteria_to_form(criteria: Criteria) -> dict[str, str]:
    return {
        "avis_max": _text(criteria.max_reviews), "avis_min": _text(criteria.min_reviews),
        "site": criteria.website, "telephone": criteria.phone,
        "franchises": "on" if criteria.exclude_franchises else "",
        "jours": str(criteria.created_within_days), "effectif_max": criteria.max_workforce or "",
        "score_site_max": _text(criteria.max_site_score), "sans_formulaire": criteria.no_form,
        "sans_https": criteria.no_https, "non_mobile": criteria.not_mobile,
    }  # fmt: skip


def request_to_form(request: CampaignRequest) -> dict[str, str]:
    """Pour pré-remplir le formulaire depuis un modèle (C18)."""
    values = {
        "nom": request.name, "metiers": ", ".join(request.trades), "nombre": str(request.target),
        "synonymes": "on" if request.synonyms_on else "", **criteria_to_form(request.criteria),
        "departements": ", ".join(z.code for z in request.zones if isinstance(z, DepartmentZone)),
        "commune": "", "ville": "", "rayon": "0",
        "pays": request.zones[0].city.country if isinstance(request.zones[0], RadiusZone)
        else request.zones[0].country,
        **{f"source_{s}": "on" for s in request.sources},
    }  # fmt: skip
    for zone in request.zones:
        if isinstance(zone, (CityZone, RadiusZone)):
            city = zone if isinstance(zone, CityZone) else zone.city
            values.update(commune=commune_value(city), ville=city.label)
            values["rayon"] = str(zone.radius_km) if isinstance(zone, RadiusZone) else "0"
    return values
