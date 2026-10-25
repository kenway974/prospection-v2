"""C06 : liste des bases Notion partagées avec l'intégration."""

import json

import pytest

from prospection.crm.notion import NotionDatabase, NotionUnavailable, list_notion_databases
from tests.fake_http import Handler, fake_client, html_reply, json_reply, timeout

TOKEN = "ntn_jeton"


def database(id_: str, title: str) -> dict[str, object]:
    return {"object": "database", "id": id_, "title": [{"plain_text": title}]}


def test_C06_databases_listed_sorted() -> None:
    body = {"results": [database("b", "Zèbre"), database("a", "Prospects v2")]}
    client, recorder = fake_client(json_reply(200, body))
    assert list_notion_databases(client, TOKEN) == [
        NotionDatabase("a", "Prospects v2"),
        NotionDatabase("b", "Zèbre"),
    ]
    request = recorder.requests[0]
    assert str(request.url) == "https://api.notion.com/v1/search"
    assert json.loads(request.content) == {"filter": {"property": "object", "value": "database"}}


def test_C06_untitled_database() -> None:
    client, _ = fake_client(
        json_reply(200, {"results": [{"object": "database", "id": "x", "title": []}]})
    )
    assert list_notion_databases(client, TOKEN) == [NotionDatabase("x", "Sans titre")]


@pytest.mark.parametrize(
    "handler",
    [html_reply(200), json_reply(200, {"results": "pas une liste"}), json_reply(401, {}), timeout],
)
def test_notion_search_response_validated(handler: Handler) -> None:
    client, _ = fake_client(handler)
    with pytest.raises(NotionUnavailable) as error:
        list_notion_databases(client, TOKEN)
    assert TOKEN not in str(error.value)
