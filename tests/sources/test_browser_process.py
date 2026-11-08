"""C166 (relecture) : la lecture par navigateur tourne dans un processus séparé, tué avec
tout ce qu'il a lancé à l'échéance ; un site qui boucle ne bloque jamais la tâche de fond.
Le faux serveur est local (aucun réseau) : chaque site lui est demandé (TEST_SERVICES_URL)."""

import subprocess
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from prospection.sources.browser_process import _kill_session, render_isolated

LOOP = "<html><body><div id='root'></div><script>onload = () => setTimeout(() => {while (true) {}}, 200)</script></body></html>"  # noqa: E501
DRAWN = """<html><body><div id="root"></div><script>
document.getElementById("root").innerHTML = "<form><input type='email'></form>";</script>
</body></html>"""


class _Site(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        target = parse_qs(urlsplit(self.path).query).get("url", [""])[0]
        body = (LOOP if target.endswith("/boucle") else DRAWN).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def fake_site() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Site)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _browsers() -> int:
    count = 0
    for cmdline in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            count += b"--headless" in cmdline.read_bytes()
        except OSError:
            continue
    return count


def test_C166_drawn_page_comes_back_from_the_separate_process(fake_site: str) -> None:
    result = render_isolated("https://p.fr/", 10, fake_site)
    assert result.page is not None, result.problem
    assert "<form>" in result.page.html


def test_C166_endless_script_is_killed_with_its_browser(fake_site: str) -> None:
    before = _browsers()
    start = time.monotonic()
    result = render_isolated("https://p.fr/boucle", 3, fake_site)
    assert result.page is None and result.problem == "Site trop lent : lecture abandonnée"
    assert time.monotonic() - start < 8
    time.sleep(0.5)
    assert _browsers() <= before


def test_C166_whole_session_is_killed_even_detached_children() -> None:
    """Un enfant qui survit à son parent (Chromium détaché) est tué aussi."""
    parent = subprocess.Popen(["/bin/sh", "-c", "sleep 60 & echo $!; wait"],
                              stdout=subprocess.PIPE, start_new_session=True)  # fmt: skip
    assert parent.stdout is not None
    child = int(parent.stdout.readline())
    _kill_session(parent.pid)
    parent.wait(timeout=5)
    time.sleep(0.2)
    state = Path(f"/proc/{child}/stat")
    assert not state.exists() or state.read_text().rsplit(")", 1)[1].split()[0] == "Z"
