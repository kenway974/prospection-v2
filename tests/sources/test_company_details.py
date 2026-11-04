"""C149 : ce que le registre gratuit dit de l'activité (labels, établissements), par SIREN."""

import pytest

from prospection.sources.company_details import company_by_siren
from prospection.sources.company_registry import RegistryUnavailable
from tests.fake_http import fake_client, json_reply, timeout
from tests.sources.test_company_registry import page, result

DETAILS = {
    "complements": {"est_rge": True, "est_qualiopi": False, "est_bio": None,
                    "est_patrimoine_vivant": True, "liste_idcc": ["1596"]},
    "nombre_etablissements_ouverts": 3,
}  # fmt: skip


def test_C149_labels_sites_and_branch_activity() -> None:
    siege = {**result()["siege"], "activite_principale": "43.22A"}  # type: ignore[dict-item]
    client, recorder = fake_client(json_reply(200, page(result(**DETAILS, siege=siege))))
    company = company_by_siren(client, "912345678")
    assert company is not None
    assert company.labels == ("est_rge", "est_patrimoine_vivant")
    assert company.open_sites == 3 and company.site_naf == "43.22A"
    assert company.leaders and company.finances  # complète les entreprises venues de Sirène
    assert recorder.requests[0].url.params["q"] == "912345678"


def test_C149_other_siren_or_nothing_found() -> None:
    client, _ = fake_client(json_reply(200, page(result(siren="999999999"))))
    assert company_by_siren(client, "912345678") is None
    client, _ = fake_client(timeout)
    with pytest.raises(RegistryUnavailable):
        company_by_siren(client, "912345678")


def test_C149_non_diffusible_keeps_no_labels() -> None:
    client, _ = fake_client(json_reply(200, page(result(**DETAILS, statut_diffusion="P"))))
    company = company_by_siren(client, "912345678")
    assert company is not None and company.labels == () and company.open_sites is None
