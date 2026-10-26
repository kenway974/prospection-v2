"""C44, C45, C93 : entreprise du registre, rapprochement sûr, non-diffusion."""

import dataclasses
from datetime import date

from prospection.domain.company import Company, describe, match_company, postal_code

LYON_SAS = Company(
    siren="912345678", name="CUISINES MARTIN", other_names=("CUISINES MARTIN LYON",),
    postal_code="69002", city="LYON", created=date(2022, 3, 1), active=True,
    legal_form="5710", naf="43.32A", workforce="03",
    leaders=("Marie DUPONT (Présidente)",), finances=(2024, 450_000, 32_000), diffusible=True,
)  # fmt: skip


def test_C45_sure_match_needs_same_name_and_postal_code() -> None:
    result = match_company("Cuisines Martin", "69002", [LYON_SAS])
    assert result.company == LYON_SAS and result.sure


def test_C45_legal_suffix_and_shop_sign_tolerated() -> None:
    assert match_company("Cuisines Martin SAS", "69002", [LYON_SAS]).sure
    assert match_company("Cuisines Martin Lyon", "69002", [LYON_SAS]).sure


def test_C45_other_postal_code_or_two_candidates_is_not_sure() -> None:
    assert not match_company("Cuisines Martin", "69003", [LYON_SAS]).sure
    twin = dataclasses.replace(LYON_SAS, siren="987654321")
    result = match_company("Cuisines Martin", "69002", [LYON_SAS, twin])
    assert not result.sure and result.company is None
    assert not match_company("Martin", "69002", [LYON_SAS]).sure  # un seul mot : trop vague


def test_postal_code_read_from_address() -> None:
    assert postal_code("12 rue de la République, 69002 Lyon, France") == "69002"
    assert postal_code("Lyon") is None


def test_C44_company_described_in_plain_words() -> None:
    lines = describe(LYON_SAS)
    assert lines == [
        ("SIREN", "912 345 678"), ("Création", "01/03/2022"), ("Forme", "SAS"),
        ("Activité", "43.32A"), ("Effectif", "6 à 9 salariés"),
        ("Dirigeants", "Marie DUPONT (Présidente)"),
        ("Chiffre d'affaires 2024", "450 000 €"), ("Résultat 2024", "32 000 €"),
    ]  # fmt: skip


def test_C44_missing_finances_said_not_published() -> None:
    bare = dataclasses.replace(LYON_SAS, finances=None, workforce=None, legal_form="9999")
    lines = dict(describe(bare))
    assert lines["Chiffre d'affaires"] == "non publié"
    assert lines["Effectif"] == "non publié" and lines["Forme"] == "autre forme (code 9999)"


def test_C93_non_diffusible_keeps_nothing_personal() -> None:
    hidden = dataclasses.replace(LYON_SAS, diffusible=False)
    assert describe(hidden) == [("Registre", "Données non diffusées à la demande de l'entreprise.")]
