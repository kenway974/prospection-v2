"""C03 : le jeton Notion est testé, avec un message clair."""

from prospection.crm.notion import check_notion_token
from prospection.domain.key_check import KeyCheck
from tests.fake_http import fake_client, html_reply, json_reply, timeout

TOKEN = "ntn_jeton_de_test"


def test_C03_valid() -> None:
    client, recorder = fake_client(json_reply(200, {"object": "user", "id": "u1"}))
    assert check_notion_token(client, TOKEN) == KeyCheck(True, "Jeton Notion valide.")
    request = recorder.requests[0]
    assert str(request.url) == "https://api.notion.com/v1/users/me"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.headers["Notion-Version"] == "2022-06-28"


def test_C03_refused() -> None:
    client, _ = fake_client(json_reply(401, {"object": "error", "code": "unauthorized"}))
    assert check_notion_token(client, TOKEN) == KeyCheck(
        False, "Jeton refusé par Notion : copiez le « secret » de votre intégration."
    )


def test_C03_timeout() -> None:
    client, _ = fake_client(timeout)
    assert check_notion_token(client, TOKEN) == KeyCheck(
        False, "Notion ne répond pas. Réessayez dans un instant."
    )


def test_C03_unexpected_html() -> None:
    client, _ = fake_client(html_reply(200))
    assert check_notion_token(client, TOKEN) == KeyCheck(
        False, "Réponse inattendue de Notion. Réessayez plus tard."
    )
