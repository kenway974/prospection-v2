"""Lire un site affiché seulement par JavaScript avec un vrai navigateur, sans IA (C166).

Chromium exécute le JavaScript, mais ne touche jamais le réseau lui-même : chaque requête est
interceptée et servie par le client protégé des sites (`safe_network` : jamais d'adresse
interne). Les adresses refusées par `allowed_url`, tout ce qui n'est pas une lecture (envoi de
formulaire, mesure d'audience) et les images, vidéos et polices sont bloqués. Un proxy mort
arrête ce qui échapperait à l'interception (WebSocket), WebRTC est coupé (UDP). Taille, nombre
de requêtes et durée bornés (règle 4) ; `browser_process` tue le tout à l'échéance.
"""

import time
from contextlib import suppress

import httpcore
import httpx
from playwright.sync_api import Error as BrowserError
from playwright.sync_api import Route, sync_playwright

from prospection.sources.read_deadline import deadline
from prospection.sources.web_reader import (
    MAX_BYTES,
    SLOW,
    UNREACHABLE,
    ReadResult,
    WebPage,
    allowed_url,
)

MAX_SECONDS = 20.0
RESOURCE_SECONDS = 8.0
MAX_RESOURCE = 5_000_000  # gros fichier JavaScript des constructeurs
MAX_TOTAL = 15_000_000
MAX_REQUESTS = 100
REFUSED = "Adresse du site refusée"
_SKIPPED = frozenset({"image", "media", "font", "websocket", "eventsource", "manifest"})
_KEPT_HEADERS = ("content-type", "location", "cache-control")
_DEAD_PROXY = "http://127.0.0.1:9"
_ARGS = ["--webrtc-ip-handling-policy=disable_non_proxied_udp", "--proxy-bypass-list=<-loopback>"]
_NO_WEBRTC = "for (const n of ['RTCPeerConnection', 'webkitRTCPeerConnection']) delete window[n];"


class _Server:
    """Sert les requêtes du navigateur par le client protégé, dans un budget d'octets."""

    def __init__(self, client: httpx.Client, until: float) -> None:
        self.client, self.left, self.until, self.count = client, MAX_TOTAL, until, 0

    def __call__(self, route: Route) -> None:
        request = route.request
        reply, open_ = None, time.monotonic() < self.until and self.count < MAX_REQUESTS
        if open_ and request.method == "GET" and request.resource_type not in _SKIPPED:
            self.count += 1
            reply = self._fetch(request.url) if allowed_url(request.url) else None
        with suppress(BrowserError):  # page déjà fermée
            if reply is None:
                route.abort()
            else:
                route.fulfill(status=reply[0], headers=reply[1], body=reply[2])

    def _fetch(self, url: str) -> tuple[int, dict[str, str], bytes] | None:
        body, limit = bytearray(), min(MAX_RESOURCE, self.left)
        try:
            left = min(RESOURCE_SECONDS, self.until - time.monotonic())
            with deadline(left), self.client.stream("GET", url) as response:
                for chunk in response.iter_bytes():  # décompressé, mais borné en taille
                    body += chunk
                    if len(body) > limit:
                        return None
        except (httpx.HTTPError, httpcore.TimeoutException):
            return None
        self.left -= len(body)
        kept = {k: response.headers[k] for k in _KEPT_HEADERS if k in response.headers}
        return response.status_code, kept, bytes(body)


def render_page(
    client: httpx.Client, url: str, seconds: float = MAX_SECONDS, executable: str | None = None
) -> ReadResult:
    """La page telle que le navigateur la dessine, ou le problème dit simplement.
    `executable` : Chromium installé ailleurs que l'emplacement par défaut."""
    if not allowed_url(url):
        return ReadResult(None, REFUSED)
    start, limit = time.monotonic(), min(seconds, MAX_SECONDS) * 1000
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=executable, proxy={"server": _DEAD_PROXY}, args=_ARGS
            )
            try:
                context = browser.new_context(service_workers="block", accept_downloads=False)
                context.add_init_script(_NO_WEBRTC)
                context.route("**/*", _Server(client, start + limit / 1000))
                page = context.new_page()
                response = page.goto(url, wait_until="load", timeout=limit)
                if response is not None and response.status >= 400:
                    return ReadResult(None, f"Le site répond une erreur {response.status}")
                left = limit - (time.monotonic() - start) * 1000
                with suppress(BrowserError):  # requêtes sans fin : on garde ce qui est dessiné
                    page.wait_for_load_state("networkidle", timeout=max(left, 1))
                html, final = page.content(), page.url
            finally:
                browser.close()
    except BrowserError as error:
        return ReadResult(None, SLOW if "Timeout" in str(error) else UNREACHABLE)
    seconds_spent = time.monotonic() - start
    page_html = html[:MAX_BYTES]
    return ReadResult(WebPage(final, page_html, seconds_spent, truncated=len(html) > MAX_BYTES))
