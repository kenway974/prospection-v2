"""Session expirée pendant une action HTMX : retour propre à la connexion."""

from fastapi.testclient import TestClient


def test_htmx_request_with_expired_session_gets_hx_redirect(client: TestClient) -> None:
    response = client.post(
        "/reglages/cles/google/tester",
        headers={
            "Origin": "https://testserver",
            "HX-Request": "true",
            "HX-Current-URL": "https://testserver/reglages/cles",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert response.headers["hx-redirect"] == "/connexion?suite=/reglages/cles"
    assert response.text == ""


def test_plain_request_with_expired_session_still_303(client: TestClient) -> None:
    response = client.get("/reglages/cles", follow_redirects=False)
    assert response.status_code == 303
