"""C84 : HTTPS uniquement ; en-têtes de sécurité ; origine vérifiée."""

from fastapi.testclient import TestClient

EXPECTED_HEADERS = {
    "content-security-policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; manifest-src 'self'; worker-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'self'"
    ),
    "x-content-type-options": "nosniff",
    "referrer-policy": "same-origin",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "permissions-policy": "camera=(), microphone=(), geolocation=(self)",
}


def test_C84_security_headers_on_every_response(client: TestClient) -> None:
    for path in ["/sante", "/page-qui-n-existe-pas"]:
        response = client.get(path)
        for name, value in EXPECTED_HEADERS.items():
            assert response.headers[name] == value, (path, name)


def test_C84_health_check_answers_ok(client: TestClient) -> None:
    response = client.get("/sante")
    assert (response.status_code, response.text) == (200, "ok")


def test_C84_http_is_redirected_to_https(client: TestClient) -> None:
    response = client.get(
        "/chemin?x=1", headers={"X-Forwarded-Proto": "http"}, follow_redirects=False
    )
    assert response.status_code == 308
    assert response.headers["location"] == "https://testserver/chemin?x=1"


def test_C84_health_check_is_not_redirected(client: TestClient) -> None:
    response = client.get("/sante", headers={"X-Forwarded-Proto": "http"})
    assert response.status_code == 200


def test_cross_site_post_is_refused(client: TestClient) -> None:
    response = client.post("/connexion", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert response.text == (
        "Action refusée : elle ne vient pas de l'app. Rechargez la page et réessayez."
    )


def test_post_without_origin_or_referer_is_refused(client: TestClient) -> None:
    assert client.post("/connexion").status_code == 403


def test_same_origin_post_passes_the_check(client: TestClient) -> None:
    response = client.post("/sante", headers={"Origin": "https://testserver"})
    assert response.status_code == 405


def test_same_origin_referer_passes_the_check(client: TestClient) -> None:
    response = client.post("/sante", headers={"Referer": "https://testserver/connexion"})
    assert response.status_code == 405


def test_C84_forwarded_proto_is_read_leniently(client: TestClient) -> None:
    for value in ["HTTP", "http, https", " http"]:
        response = client.get(
            "/chemin", headers={"X-Forwarded-Proto": value}, follow_redirects=False
        )
        assert response.status_code == 308, value


def test_pages_are_not_cached_but_static_files_are(client: TestClient) -> None:
    assert client.get("/connexion").headers["cache-control"] == "no-store"
    assert "no-store" not in client.get("/static/app.css").headers.get("cache-control", "")
