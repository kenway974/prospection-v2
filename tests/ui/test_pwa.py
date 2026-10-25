"""C116 : l'app s'installe sur Android."""

import json
import struct

from fastapi.testclient import TestClient

from prospection.ui.paths import STATIC_DIR


def png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def test_C116_manifest_is_valid_and_linked(client: TestClient) -> None:
    page = client.get("/connexion").text
    assert '<link rel="manifest" href="/static/manifest.webmanifest">' in page
    assert '<meta name="theme-color" content="#1A3E8F">' in page
    response = client.get("/static/manifest.webmanifest")
    assert response.status_code == 200
    manifest = json.loads(response.content)
    expected = {
        "name": "Prospection",
        "short_name": "Prospection",
        "lang": "fr",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#F2F2F7",
        "theme_color": "#1A3E8F",
    }
    assert {key: manifest[key] for key in expected} == expected
    sizes = {(icon["sizes"], icon.get("purpose", "any")) for icon in manifest["icons"]}
    assert sizes == {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")}
    for icon in manifest["icons"]:
        data = (STATIC_DIR / icon["src"].removeprefix("/static/")).read_bytes()
        width, height = png_size(data)
        assert f"{width}x{height}" == icon["sizes"]


def test_C116_service_worker_served_at_root_without_session(client: TestClient) -> None:
    response = client.get("/service-worker.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.headers["service-worker-allowed"] == "/"
    assert response.headers["cache-control"] == "no-cache"


def test_C116_service_worker_is_registered_by_external_script(client: TestClient) -> None:
    assert '<script src="/static/app.js" defer></script>' in client.get("/connexion").text
    assert "serviceWorker.register" in client.get("/static/app.js").text
