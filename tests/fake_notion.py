"""Faux Notion pour les tests : base en mémoire, aucun appel réseau."""

import json

import httpx


class FakeNotion:
    """Base Notion en mémoire : pages par id, avec leurs propriétés au format de l'API."""

    def __init__(self) -> None:
        self.pages: dict[str, dict[str, object]] = {}
        self.calls: list[httpx.Request] = []
        self.answer: httpx.Response | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if self.answer is not None:
            return self.answer
        body = json.loads(request.content) if request.content else {}
        if request.url.path.endswith("/query"):
            wanted = body.get("filter")
            hits = [p for p in self.pages.values() if not wanted or _text(p, wanted["property"])
                    == wanted["rich_text"]["equals"]]  # fmt: skip
            return httpx.Response(200, json={"results": hits[:100], "has_more": False})
        page_id = (
            request.url.path.rsplit("/", 1)[-1]
            if request.method == "PATCH"
            else f"p{len(self.pages) + 1}"
        )
        page = self.pages.setdefault(page_id, {"id": page_id, "url": f"https://notion.so/{page_id}",
                                               "properties": {}})  # fmt: skip
        page["properties"].update(_as_read(body["properties"]))  # type: ignore[attr-defined]
        return httpx.Response(200, json=page)


def _as_read(props: dict[str, dict[str, object]]) -> dict[str, object]:
    """Propriétés écrites -> propriétés telles que Notion les relit."""
    read: dict[str, object] = {}
    for name, prop in props.items():
        kind, value = next(iter(prop.items()))
        if kind in ("title", "rich_text"):
            value = [{"plain_text": part["text"]["content"]} for part in value]  # type: ignore[attr-defined]
        read[name] = {"type": kind, kind: value}
    return read


def _text(page: dict[str, object], prop: str) -> str | None:
    found = page["properties"].get(prop)  # type: ignore[attr-defined]
    return "".join(p["plain_text"] for p in found["rich_text"]) if found else None
