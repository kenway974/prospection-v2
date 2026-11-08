"""C166 : lecture par un vrai navigateur. Chromium ne touche jamais le réseau : chaque
requête passe par le client protégé (ici un faux serveur), jamais vers une adresse interne."""

import os

import httpx

from prospection.sources.browser_reader import render_page
from tests.fake_http import fake_client

CHROMIUM = os.environ.get("CHROMIUM_PATH")  # navigateur installé ailleurs (poste local)
SHELL = """<!doctype html><html><head><meta name="viewport" content="w">
<script src="/app.js"></script></head><body><div id="root"></div></body></html>"""
APP = """
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("root").innerHTML =
    '<h1>Paysagiste</h1><form><input type="email" name="email"><textarea></textarea></form>';
  fetch("http://127.0.0.1:8080/secret").catch(() => {});
  fetch("https://metadata.internal/").catch(() => {});
  fetch("https://p.fr/envoi", {method: "POST", body: "x"}).catch(() => {});
  new Image().src = "https://p.fr/photo.png";
});
"""


def _site(request: httpx.Request) -> httpx.Response:
    bodies = {"/": ("text/html", SHELL), "/app.js": ("text/javascript", APP)}
    kind, body = bodies.get(request.url.path, ("text/plain", ""))
    return httpx.Response(200 if body else 404, headers={"Content-Type": kind}, text=body)


def test_C166_javascript_is_run_and_the_drawn_page_is_returned() -> None:
    client, recorder = fake_client(_site)
    result = render_page(client, "https://p.fr/", 15, CHROMIUM)
    assert result.page is not None, result.problem
    assert "<form>" in result.page.html and "Paysagiste" in result.page.html
    assert result.page.url == "https://p.fr/"
    asked = [(r.method, str(r.url)) for r in recorder.requests]
    assert asked == [("GET", "https://p.fr/"), ("GET", "https://p.fr/app.js")]  # rien d'autre


def test_C166_internal_address_is_refused_without_opening_the_browser() -> None:
    client, recorder = fake_client(_site)
    result = render_page(client, "http://127.0.0.1/", 15, CHROMIUM)
    assert result.page is None and result.problem == "Adresse du site refusée"
    assert recorder.requests == []


def test_C166_error_page_is_reported_simply() -> None:
    client, _ = fake_client(lambda r: httpx.Response(500, text="erreur"))
    result = render_page(client, "https://p.fr/", 15, CHROMIUM)
    assert result.page is None and result.problem == "Le site répond une erreur 500"
