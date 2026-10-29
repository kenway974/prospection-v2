"""C134, C135 : villes proposées pendant la frappe ; bouton occupé pendant une action longue."""

import os

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def _login(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/connexion")
    page.get_by_label("Mot de passe").fill(os.environ["E2E_PASSWORD"])
    page.get_by_role("button", name="Se connecter").click()


def test_C134_city_list_while_typing_then_closed(page: Page, base_url: str) -> None:
    _login(page, base_url)
    page.goto(f"{base_url}/recherche")
    page.get_by_label("Pays").select_option("BE")
    page.get_by_label("Ville", exact=True).press_sequentially("Saint")  # sans quitter le champ
    choices = page.locator("#communes label.choice")
    expect(choices).to_have_count(10, timeout=5_000)
    choices.nth(1).click()
    expect(choices.filter(visible=True)).to_have_count(1)  # la ville choisie reste seule
    page.get_by_role("button", name="Changer de commune").click()
    expect(choices.filter(visible=True)).to_have_count(10)
    page.get_by_label("Ville", exact=True).press_sequentially("-")  # nouvelle frappe : liste vidée
    expect(page.locator("#communes input:checked")).to_have_count(0)


def test_C135_launch_button_says_it_is_working(page: Page, base_url: str) -> None:
    _login(page, base_url)
    page.goto(f"{base_url}/recherche")

    # Après le bouton (document), la fenêtre annule l'envoi : la page reste, on voit l'attente.
    page.evaluate("window.addEventListener('submit', (event) => event.preventDefault())")
    launch = page.locator('form[action="/recherche"] button[type="submit"]')  # son texte change
    launch.click(no_wait_after=True)
    expect(launch).to_have_attribute("aria-busy", "true")
    expect(launch).to_have_text("Lancement de la campagne…")
