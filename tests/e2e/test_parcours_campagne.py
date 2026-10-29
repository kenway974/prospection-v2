"""Parcours d'une campagne Google Maps, de la clé aux prospects qualifiés.

C10, C12, C19, C30, C33, C34, C38, C130 : la tâche de fond interroge le faux Google
(tests/e2e/fake_google.py) ; la liste noire écarte un des trois cuisinistes.
"""

import os

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.fake_google import FAKE_KEY

pytestmark = pytest.mark.e2e
# Quitter la page serait-il bloqué par « Quitter le site ? » (événement beforeunload) ?
LEAVING = """() => {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}"""


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
    assert page.evaluate(LEAVING) is False  # C130 : pas de « Quitter le site ? »
    page.get_by_role("button", name="Lancer").click()

    progress = page.locator("#progression")
    expect(progress.get_by_role("status")).to_have_text(
        "Objectif atteint : 2 prospects qualifiés.", timeout=30_000
    )
    expect(progress).to_contain_text("2 sur 2 qualifiés")
    expect(progress).to_contain_text("Liste noire")


def test_C102_C107_C109_call_session_then_today(page: Page, base_url: str) -> None:
    """Suite du parcours : les prospects trouvés s'appellent et se suivent."""
    _login(page, base_url)
    page.goto(f"{base_url}/prospects")
    page.get_by_role("button", name="Démarrer la session d'appel").click()
    page.get_by_role("button", name="Messagerie").click()
    expect(page.locator('button[value="messagerie"]')).to_have_attribute("aria-pressed", "true")
    page.get_by_role("button", name="Enregistrer l'action").click()  # « Rappeler demain » proposé
    expect(page.locator("#suivi")).to_contain_text("Enregistré")
    page.get_by_label("Nouvelle note").fill("Rappeler après 14 h")
    assert page.evaluate(LEAVING) is True  # C106 : une note pas encore ajoutée prévient
    page.get_by_role("button", name="Ajouter la note").click()
    expect(page.locator("#notes")).to_contain_text("Rappeler après 14 h")
    page.goto(f"{base_url}/")
    expect(page.get_by_text("Reprendre la session")).to_be_visible()
    expect(page.locator("main")).to_contain_text("Rappeler")


def test_C46_C52_found_site_shown_on_the_card(page: Page, base_url: str) -> None:
    """Suite du parcours : le site de Cuisines Martin, absent de sa fiche, est retrouvé."""
    _login(page, base_url)
    page.goto(f"{base_url}/prospects")
    page.get_by_role("link", name="Cuisines Martin").first.click()
    site = page.locator("section", has=page.get_by_role("heading", name="Le site"))
    expect(site).to_contain_text("Retrouvé à partir du nom")
    expect(site).to_contain_text("/100")
    expect(site.get_by_role("link", name="Facebook")).to_be_visible()
    appel = page.locator("section", has=page.get_by_role("heading", name="Pour l'appel"))
    expect(appel).to_contain_text("Indices à confirmer pendant l'appel")
    expect(page.get_by_role("link", name="Dirigeant sur LinkedIn")).to_be_visible()
    expect(page.get_by_text("Détail du score")).to_be_visible()
