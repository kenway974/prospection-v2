"""C06 : liste des bases Notion partagées avec l'intégration."""

import json

import httpx
import pytest

from prospection.crm.notion import NotionDatabase, NotionUnavailable, list_notion_databases
from tests.fake_http import Handler, fake_client, html_reply, json_reply, timeout

TOKEN = "ntn_jeton"


def database(id_: str, title: str) -> dict[str, object]:
    return {"object": "database", "id": id_, "title": [{"plain_text": title}]}


def test_C06_databases_listed_sorted() -> None:
    a, b = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    body = {"results": [database(b, "Zèbre"), database(a, "Prospects v2")]}
    client, recorder = fake_client(json_reply(200, body))
    assert list_notion_databases(client, TOKEN) == [
        NotionDatabase(a, "Prospects v2"),
        NotionDatabase(b, "Zèbre"),
    ]
    request = recorder.requests[0]
    assert str(request.url) == "https://api.notion.com/v1/search"
    assert json.loads(request.content) == {"filter": {"property": "object", "value": "database"}}


def test_C06_untitled_database() -> None:
    id_ = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    body = {"results": [{"object": "database", "id": id_, "title": []}]}
    client, _ = fake_client(json_reply(200, body))
    assert list_notion_databases(client, TOKEN) == [NotionDatabase(id_, "Sans titre")]


@pytest.mark.parametrize(
    "handler",
    [html_reply(200), json_reply(200, {"results": "pas une liste"}), json_reply(401, {}), timeout],
)
def test_notion_search_response_validated(handler: Handler) -> None:
    client, _ = fake_client(handler)
    with pytest.raises(NotionUnavailable) as error:
        list_notion_databases(client, TOKEN)
    assert TOKEN not in str(error.value)


def test_C06_pages_are_followed() -> None:
    first = "11111111-1111-1111-1111-111111111111"
    second = "22222222-2222-2222-2222-222222222222"

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("start_cursor") == "page2":
            return httpx.Response(200, json={"results": [database(second, "B")], "has_more": False})
        return httpx.Response(
            200, json={"results": [database(first, "A")], "has_more": True, "next_cursor": "page2"}
        )

    client, recorder = fake_client(handler)
    assert [db.id for db in list_notion_databases(client, TOKEN)] == [first, second]
    assert len(recorder.requests) == 2


def test_C06_database_id_must_be_a_uuid() -> None:
    client, _ = fake_client(json_reply(200, {"results": [database("../../x", "A")]}))
    with pytest.raises(NotionUnavailable):
        list_notion_databases(client, TOKEN)
