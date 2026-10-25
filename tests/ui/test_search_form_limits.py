"""C17 : saisies étranges ou démesurées refusées proprement, jamais une erreur 500."""

import time

from fastapi.testclient import TestClient

from prospection.domain.criteria import Criteria
from prospection.ui.routes_search import DEFAULTS
from prospection.ui.search_form import parse_form
from tests.ui.test_search_form import FORM, ORIGIN, client, post, text

__all__ = ["client"]  # fixture partagée


def test_C17_non_ascii_digits_refused_without_crash(client: TestClient) -> None:
    response = post(client, nombre="²", avis_max="٣")
    assert response.status_code == 400
    assert "Choisissez entre 1 et 200 prospects." in text(response)
    estimate = client.post("/recherche/estimation", data={**FORM, "nombre": "²"}, headers=ORIGIN)
    assert estimate.status_code == 200


def test_C17_too_many_departments_refused() -> None:
    parsed = parse_form({**FORM, "departements": ", ".join(["69"] * 21)})
    assert parsed.errors["zones"] == "20 départements au plus par campagne."


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


def test_C11_source_shown_google_now_registry_soon(client: TestClient) -> None:
    page = text(client.get("/recherche"))
    assert '<input type="radio" name="source" value="google" checked> Google Maps' in page
    assert "Entreprises récemment créées · bientôt" in page
