"""C28, C29 : critères sur le site dans le formulaire Recherche."""

from fastapi.testclient import TestClient

from prospection.ui.search_form import parse_form
from prospection.ui.search_form_fill import criteria_to_form
from tests.ui.test_search_form import FORM, client, text
from tests.ui.test_search_form_limits import post_form

__all__ = ["client"]  # fixture partagée


def test_C28_C29_site_criteria_offered(client: TestClient) -> None:
    page = client.get("/recherche").text
    assert '<label for="score_site_max">Score du site au plus (sur 100)</label>' in page
    for name in ("sans_formulaire", "sans_https", "non_mobile"):
        assert f'name="{name}"' in page
    assert '<option value="only">Seulement ceux-là</option>' in page


def test_C28_C29_site_criteria_read_and_refilled() -> None:
    form = {**FORM, "score_site_max": "50", "sans_formulaire": "only", "non_mobile": "exclude"}
    criteria = parse_form(form).raw.criteria
    assert (criteria.max_site_score, criteria.no_form, criteria.not_mobile) == (
        50,
        "only",
        "exclude",
    )
    assert criteria.no_https == "any"
    refilled = criteria_to_form(criteria)
    assert (refilled["score_site_max"], refilled["sans_formulaire"]) == ("50", "only")


def test_C28_bad_score_refused_with_what_to_do(client: TestClient) -> None:
    response = post_form(client, {**FORM, "score_site_max": "0"})
    assert response.status_code == 400
    assert "Choisissez un score entre 1 et 100, ou laissez vide." in text(response)
