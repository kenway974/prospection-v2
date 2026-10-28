"""C68 à C75 : pages de la base Notion, avec un faux Notion (aucun réseau)."""

import json

import httpx
import pytest

from prospection.crm.notion_pages import (
    NotionBusy,
    NotionRefused,
    create_page,
    find_page,
    index_pages,
    update_page,
)
from tests.fake_http import fake_client

DB = "ebbf6ef71a4945bf8575a326c745d824"
PAGE = {
    "id": "p-1", "url": "https://www.notion.so/p-1",
    "properties": {
        "Entreprise": {"type": "title", "title": [{"plain_text": "Atelier"}]},
        "Téléphone": {"type": "phone_number", "phone_number": "+33612345678"},
        "Score": {"type": "number", "number": 60},
        "Email": {"type": "email", "email": None},
        "Date action": {"type": "date", "date": {"start": "2026-11-02"}},
        "SIREN": {"type": "rich_text", "rich_text": [{"plain_text": "912345678"}]},
        "ID app": {"type": "rich_text", "rich_text": [{"plain_text": "place-1"}]},
    },
}  # fmt: skip


def test_C69_found_by_app_id_then_siren_with_its_values() -> None:
    queries: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        queries.append(body["filter"])
        hit = body["filter"]["property"] == "SIREN"
        return httpx.Response(200, json={"results": [PAGE] if hit else [], "has_more": False})

    client, _ = fake_client(handler)
    page = find_page(client, "secret", DB, "place-9", "912345678")
    assert page is not None and page.id == "p-1" and page.url == "https://www.notion.so/p-1"
    assert page.values["Téléphone"] == "+33612345678" and page.values["Score"] == 60
    assert page.values["Email"] is None and page.values["Date action"] == "2026-11-02"
    assert [q["property"] for q in queries] == ["ID app", "SIREN"]


def test_C68_create_and_update() -> None:
    client, recorder = fake_client(lambda r: httpx.Response(200, json=PAGE))
    assert create_page(client, "secret", DB, {"Entreprise": {"title": []}}) == ("p-1", PAGE["url"])
    assert update_page(client, "secret", "p-1", {"Score": {"number": 75}}) == PAGE["url"]
    created, updated = recorder.requests
    assert json.loads(created.content)["parent"] == {"database_id": DB}
    assert (updated.method, updated.url.path) == ("PATCH", "/v1/pages/p-1")


@pytest.mark.parametrize(
    ("reply", "error"),
    [(httpx.Response(429, headers={"Retry-After": "3"}), NotionBusy),
     (httpx.Response(502), NotionBusy),
     (httpx.Response(400, json={"message": "Score is expected to be number."}), NotionRefused),
     (httpx.Response(404, json={"message": "Could not find database"}), NotionRefused)],
)  # fmt: skip
def test_C73_busy_or_refused(reply: httpx.Response, error: type[Exception]) -> None:
    client, _ = fake_client(lambda r: reply)
    with pytest.raises(error) as raised:
        create_page(client, "secret", DB, {})
    if isinstance(raised.value, NotionBusy) and reply.status_code == 429:
        assert raised.value.retry_after == 3.0
    if reply.status_code == 404:
        assert "Connexions" in str(raised.value)  # dit quoi faire


def test_C32_index_read_page_by_page() -> None:
    pages = iter([{"results": [PAGE], "has_more": True, "next_cursor": "c2"},
                  {"results": [], "has_more": False}])  # fmt: skip
    client, _ = fake_client(lambda r: httpx.Response(200, json=next(pages)))
    entries, cursor = index_pages(client, "secret", DB, None)
    assert entries == [("place-1", "912345678", "Atelier", None)] and cursor == "c2"
    assert index_pages(client, "secret", DB, cursor) == ([], None)


def test_C75_requests_spaced_whatever_the_thread() -> None:
    import time

    from prospection.crm.notion_pages import MIN_INTERVAL, Pacer

    pacer = Pacer(0.05)
    start = time.monotonic()
    for _ in range(4):
        pacer.wait()
    assert time.monotonic() - start >= 0.15 and MIN_INTERVAL >= 0.33
