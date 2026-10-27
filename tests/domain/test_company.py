"""C44, C45, C93 : entreprise du registre, rapprochement sûr, non-diffusion."""

import dataclasses
from datetime import date

from prospection.domain.company import Company, match_company, postal_code
from prospection.domain.company_card import (
    NON_DIFFUSIBLE,
    NOT_FRENCH,
    TO_CONFIRM,
    describe,
    registry_lines,
)

LYON_SAS = Company(
    siren="912345678", name="CUISINES MARTIN", other_names=("CUISINES MARTIN LYON",),
    postal_code="69002", city="LYON", created=date(2022, 3, 1), active=True,
    legal_form="5710", naf="43.32A", workforce="03",
    leaders=("Marie DUPONT (Présidente)",), finances=(2024, 450_000, 32_000), diffusible=True,
    siret="91234567800012",
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
        ("SIREN", "912 345 678"), ("SIRET", "912 345 678 00012"), ("Création", "01/03/2022"),
        ("Forme", "SAS"), ("Activité", "Travaux de menuiserie bois et PVC (43.32A)"),
        ("Effectif", "6 à 9 salariés"),
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


def test_C44_unknown_staff_and_activity_said_plainly() -> None:
    lines = dict(describe(dataclasses.replace(LYON_SAS, workforce="NN", naf="99.99Z")))
    assert lines["Effectif"] == "non employeuse ou effectif non déclaré"
    assert lines["Activité"] == "99.99Z"


def test_C45_closed_company_is_never_sure() -> None:
    closed = dataclasses.replace(LYON_SAS, active=False)
    assert not match_company("Cuisines Martin", "69002", [closed]).sure


def test_C45_extra_words_allowed_only_for_the_city() -> None:
    no_sign = dataclasses.replace(LYON_SAS, other_names=())
    assert match_company("Cuisines Martin Lyon", "69002", [no_sign]).sure
    paul = dataclasses.replace(no_sign, name="CHEZ PAUL IMMOBILIER")
    assert not match_company("Chez Paul", "69002", [paul]).sure
    fournil = dataclasses.replace(no_sign, name="LE FOURNIL DE LA GARE")
    assert not match_company("Le Fournil", "69002", [fournil]).sure


def test_C45_shop_away_from_head_office_is_found_with_its_siret() -> None:
    head_office_elsewhere = dataclasses.replace(
        LYON_SAS, postal_code="69006", branches=(("91234567800020", "69002"),)
    )
    result = match_company("Cuisines Martin", "69002", [head_office_elsewhere])
    assert result.sure and result.company is not None
    assert result.company.siret == "91234567800020" and result.company.branches == ()


def test_C44_registry_block_says_where_things_stand() -> None:
    assert registry_lines(None, None) == [
        ("Registre", "Pas encore rapprochée du registre des entreprises.")
    ]
    assert "à confirmer" in registry_lines(None, TO_CONFIRM)[0][1]
    assert "hors de France" in registry_lines(None, NOT_FRENCH)[0][1]
    assert registry_lines(None, NON_DIFFUSIBLE) == [
        ("Registre", "Données non diffusées à la demande de l'entreprise.")
    ]
    assert registry_lines(LYON_SAS, "sûr")[0] == ("SIREN", "912 345 678")
