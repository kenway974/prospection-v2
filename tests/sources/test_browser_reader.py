"""C166 : lecture par un vrai navigateur. Chromium ne touche jamais le réseau : chaque
requête passe par le client protégé (ici un faux serveur), jamais vers une adresse interne."""

import os
import socket
import time

import httpx
import pytest

from prospection.sources.browser_reader import render_page
from tests.fake_http import fake_client

HTML = {"Content-Type": "text/html"}
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


def test_C166_webrtc_never_reaches_an_internal_address() -> None:
    """Relecture : STUN passe en UDP, hors du proxy et de l'interception."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.bind(("127.0.0.1", 0))
    listener.settimeout(1.5)
    port = listener.getsockname()[1]
    script = f"""<html><body><div id="root">x</div><script>
      try {{ const pc = new RTCPeerConnection({{iceServers: [{{urls: "stun:127.0.0.1:{port}"}}]}});
             pc.createDataChannel("x"); pc.createOffer().then(o => pc.setLocalDescription(o));
      }} catch (e) {{}}
    </script></body></html>"""
    client, _ = fake_client(lambda r: httpx.Response(200, headers=HTML, text=script))
    render_page(client, "https://p.fr/", 5, CHROMIUM)
    with pytest.raises(TimeoutError):
        listener.recvfrom(100)
    listener.close()


def test_C166_slow_resources_cannot_stretch_the_reading() -> None:
    """Relecture : 30 scripts lents servis un par un dépassaient largement la durée."""
    shell = "<html><head>" + "".join(f'<script src="/s{i}.js"></script>' for i in range(30))

    def slow(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(200, headers=HTML, text=shell + "</head><body></body></html>")
        time.sleep(0.5)
        return httpx.Response(200, headers={"Content-Type": "text/javascript"}, text="1;")

    client, recorder = fake_client(slow)
    start = time.monotonic()
    render_page(client, "https://p.fr/", 3, CHROMIUM)
    assert time.monotonic() - start < 6
    assert len(recorder.requests) < 12
