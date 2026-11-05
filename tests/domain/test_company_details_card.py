"""C149, C150 : la fiche dit tout ce que les registres savent de l'activité, en clair."""

import dataclasses

from prospection.domain.company_card import describe
from tests.domain.test_company import LYON_SAS


def test_C149_labels_sites_and_branch_activity_in_plain_words() -> None:
    company = dataclasses.replace(LYON_SAS, labels=("est_rge", "est_patrimoine_vivant"),
                                  open_sites=3, site_naf="43.22A")  # fmt: skip
    lines = dict(describe(company))
    assert (
        lines["Labels"]
        == "RGE (Reconnu garant de l'environnement), Entreprise du patrimoine vivant"
    )
    assert lines["Établissements ouverts"] == "3"
    assert lines["Activité de l'établissement"].startswith("Travaux d'installation d'eau et de gaz")


def test_C150_declared_purpose_activities_and_domains() -> None:
    company = dataclasses.replace(
        LYON_SAS,
        purpose="Conception et pose de cuisines.",
        activities=("Pose de cuisines équipées (artisanale)",),
        domains=("cuisines-martin.fr",),
    )
    lines = dict(describe(company))
    assert lines["Objet social"] == "Conception et pose de cuisines."
    assert lines["Activités déclarées"] == "Pose de cuisines équipées (artisanale)"
    assert lines["Sites déclarés"] == "cuisines-martin.fr"


def test_C149_nothing_invented_when_unknown() -> None:
    lines = dict(describe(LYON_SAS))
    assert not {"Labels", "Objet social", "Établissements ouverts"} & set(lines)
