"""C17 : saisies étranges ou démesurées refusées proprement, jamais une erreur 500."""

import time

from fastapi.testclient import TestClient

from prospection.domain.criteria import Criteria
from prospection.ui.routes_search import DEFAULTS
from prospection.ui.search_form import parse_form
from tests.ui.test_search_form import FORM, ORIGIN, client, post, text


def post_form(client: TestClient, form: dict[str, str]):  # type: ignore[no-untyped-def]
    return client.post("/recherche", data=form, headers=ORIGIN, follow_redirects=False)


__all__ = ["client"]  # fixture partagée


def test_C17_non_ascii_digits_refused_without_crash(client: TestClient) -> None:
    response = post(client, nombre="²", avis_max="٣")
    assert response.status_code == 400
    assert "Choisissez entre 1 et 200 prospects." in text(response)
    estimate = client.post("/recherche/estimation", data={**FORM, "nombre": "²"}, headers=ORIGIN)
    assert estimate.status_code == 200


def test_C17_too_many_departments_refused() -> None:
    parsed = parse_form({**FORM, "departements": ", ".join(["69"] * 21)})
    assert parsed.errors["zones"] == "20 départements, provinces ou cantons au plus par campagne."


def test_C16_huge_estimation_form_answered_quickly(client: TestClient) -> None:
    started = time.monotonic()
    data = {**FORM, "departements": "69, " * 100_000, "metiers": "x, " * 100_000}
    response = client.post("/recherche/estimation", data=data, headers=ORIGIN)
    assert response.status_code == 200
    assert time.monotonic() - started < 2


def test_form_defaults_are_the_criteria_defaults() -> None:
    criteria = Criteria()
    assert DEFAULTS["avis_max"] == str(criteria.max_reviews)
    assert DEFAULTS["telephone"] == criteria.phone and DEFAULTS["site"] == criteria.website
    assert parse_form({**DEFAULTS, "nom": "x", "metiers": "x"}).raw.criteria == criteria


def test_C11_sources_offered_google_checked(client: TestClient) -> None:
    page = text(client.get("/recherche"))
    assert '<input type="checkbox" name="source_google" checked> Google Maps' in page
    assert '<input type="checkbox" name="source_registre"> Entreprises récemment créées' in page
    assert '<label for="jours">Créées depuis (jours)</label>' in page


def test_C125_registry_refused_abroad_with_reason(client: TestClient) -> None:
    form = {**FORM, "pays": "BE", "commune": "", "departements": "Liège",
            "source_registre": "on"}  # fmt: skip
    form.pop("source_google", None)
    response = post_form(client, form)
    assert response.status_code == 400
    assert "Belgique : la Banque-Carrefour des Entreprises" in text(response)


def test_C16_registry_counts_the_lookup_cap(client: TestClient) -> None:
    """Chaque entreprise examinée coûte une recherche, qualifiée ou non : on annonce le plafond."""
    form = {**FORM, "source_registre": "on", "nombre": "10"}
    estimate = text(client.post("/recherche/estimation", data=form, headers=ORIGIN))
    assert "59 pages au plus" in estimate  # 9 pages Google + 5 recherches par prospect voulu
    assert "5 par prospect voulu" in estimate
