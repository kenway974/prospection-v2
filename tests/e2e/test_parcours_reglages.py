"""C02, C04 : saisir une clé dans l'app, puis ne plus jamais la voir."""

import os

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e
FAKE_KEY = "AIza-fausse-cle-de-bout-en-bout"


def test_C02_C04_save_key_then_never_shown(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/connexion")
    page.get_by_label("Mot de passe").fill(os.environ["E2E_PASSWORD"])
    page.get_by_role("button", name="Se connecter").click()
    page.get_by_role("link", name="Réglages").click()
    page.get_by_role("link", name="Clés API").click()
    google = page.locator("#cle-google")
    google.get_by_label("Nouvelle clé Google Maps").fill(FAKE_KEY)
    google.get_by_role("button", name="Enregistrer").click()
    expect(page.locator("#cle-google")).to_contain_text("Enregistrée le")
    assert FAKE_KEY not in page.content()
