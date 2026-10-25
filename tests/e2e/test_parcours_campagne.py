"""Parcours d'une campagne Google Maps, de la clé aux prospects qualifiés.

C10, C12, C19, C30, C33, C34, C38 : la tâche de fond interroge le faux Google
(tests/e2e/fake_google.py) ; la liste noire écarte un des trois cuisinistes.
"""

import os

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.fake_google import FAKE_KEY

pytestmark = pytest.mark.e2e


def _login(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/connexion")
    page.get_by_label("Mot de passe").fill(os.environ["E2E_PASSWORD"])
    page.get_by_role("button", name="Se connecter").click()


def test_campaign_from_key_to_qualified_prospects(page: Page, base_url: str) -> None:
    _login(page, base_url)
    page.goto(f"{base_url}/reglages/cles")
    google = page.locator("#cle-google")
    google.get_by_label("Nouvelle clé Google Maps").fill(FAKE_KEY)
    google.get_by_role("button", name="Enregistrer").click()
    page.goto(f"{base_url}/reglages/exclusions")
    page.get_by_label("Liste noire (un nom par ligne)").fill("Cuisines Lefèvre")
    page.get_by_role("button", name="Enregistrer").click()

    page.goto(f"{base_url}/recherche")
    page.get_by_label("Nom de la campagne").fill("Cuisinistes Rhône")
    page.get_by_label("Métiers").fill("cuisiniste")
    page.get_by_label("Départements, provinces ou cantons").fill("Rhône")
    page.get_by_label("Prospects qualifiés voulus").fill("2")
    page.get_by_role("button", name="Lancer").click()

    progress = page.locator("#progression")
    expect(progress.get_by_role("status")).to_have_text(
        "Objectif atteint : 2 prospects qualifiés.", timeout=30_000
    )
    expect(progress).to_contain_text("2 sur 2 qualifiés")
    expect(progress).to_contain_text("Liste noire")
