"""C112 : indices de santé ; « non publié » si absent, « probable » si estimé."""

import dataclasses
from datetime import date

from prospection.domain.health import health_lines
from prospection.domain.signals import signals_of
from tests.domain.test_company import LYON_SAS
from tests.storage.test_campaigns import PLACE

TODAY = date(2026, 10, 27)


def test_C112_published_figures_and_google_activity() -> None:
    hours = ("lundi: 08:00-18:00", "mardi: 08:00-18:00")
    place = dataclasses.replace(
        PLACE, review_count=12, rating=4.4, photo_count=8,
        owner_photo_estimate="probable propriétaire", opening_hours=hours,
    )  # fmt: skip
    lines = dict(health_lines(signals_of(place, None, LYON_SAS, "sûr", (), TODAY)))
    assert lines["Chiffre d'affaires 2024"] == "450 000 €"
    assert lines["Résultat 2024"] == "32 000 €"
    assert lines["Effectif"] == "6 à 9 salariés"
    assert lines["Ancienneté"] == "4 ans"
    assert lines["Horaires"] == "publiés sur Google (2 jours)"
    assert lines["Avis"] == "12 avis, note 4,4/5 (rythme non disponible)"
    assert lines["Photos"] == "8 (ajoutées par le propriétaire : probable)"


def test_C112_registry_not_consulted_yet_said_so() -> None:
    lines = dict(health_lines(signals_of(PLACE, None, None, None, (), TODAY)))
    assert lines["Chiffre d'affaires"] == "registre pas encore consulté"
    assert lines["Effectif"] == "registre pas encore consulté"
    assert lines["Horaires"] == "non publiés" and lines["Ancienneté"] == "non publiée"


def test_C112_known_company_without_figures_not_published() -> None:
    bare = dataclasses.replace(LYON_SAS, finances=None, workforce=None)
    lines = dict(health_lines(signals_of(PLACE, None, bare, "sûr", (), TODAY)))
    assert lines["Chiffre d'affaires"] == "non publié" and lines["Effectif"] == "non publié"


def test_C112_non_employer_and_missing_finances() -> None:
    company = dataclasses.replace(LYON_SAS, workforce="NN", finances=None)
    lines = dict(health_lines(signals_of(PLACE, None, company, "sûr", (), TODAY)))
    assert lines["Effectif"] == "non employeuse ou effectif non déclaré"
    assert lines["Chiffre d'affaires"] == "non publié"


def test_C93_non_diffusible_figures_never_shown() -> None:
    lines = dict(health_lines(signals_of(PLACE, None, None, "non diffusible", (), TODAY)))
    assert lines["Chiffre d'affaires"] == "non diffusé à la demande de l'entreprise"
    assert lines["Ancienneté"] == "non publiée"
