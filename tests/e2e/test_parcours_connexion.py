"""C01, C117 : se connecter puis naviguer, sur un écran de téléphone."""

import os

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_C01_C117_login_and_navigate(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/")
    expect(page.get_by_role("heading", name="Connexion")).to_be_visible()
    page.get_by_label("Mot de passe").fill(os.environ["E2E_PASSWORD"])
    page.get_by_role("button", name="Se connecter").click()
    expect(page.get_by_role("heading", name="Aujourd'hui")).to_be_visible()

    nav = page.get_by_role("navigation", name="Navigation principale")
    nav.get_by_role("link", name="Prospects").click()
    expect(page.get_by_role("heading", name="Prospects")).to_be_visible()
    expect(nav.get_by_role("link", name="Prospects")).to_have_attribute("aria-current", "page")


def test_C117_nav_never_hides_the_end_of_the_page(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/connexion")
    page.get_by_label("Mot de passe").fill(os.environ["E2E_PASSWORD"])
    page.get_by_role("button", name="Se connecter").click()
    page.goto(f"{base_url}/reglages/connexions")
    page.mouse.wheel(0, 10_000)
    last = page.get_by_role("button", name="Se déconnecter").bounding_box()
    nav = page.get_by_role("navigation", name="Navigation principale").bounding_box()
    assert last and nav
    assert last["y"] + last["height"] <= nav["y"]
