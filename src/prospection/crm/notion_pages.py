"""Pages de la base Notion « Prospects v2 » : chercher, créer, mettre à jour, relire (C32,
C68 à C75). API officielle, version épinglée. Réponses validées ; un champ inattendu est lu
comme vide, jamais inventé.

Repris de prospection-bot (services/crm/notion.py, version 530ba12) : messages 401 / 404
qui disent quoi faire, recherche de doublon avant création, mise à jour par PATCH.
"""

from dataclasses import dataclass
from typing import Any

import httpx

from prospection.crm.notion_http import (
    MIN_INTERVAL,
    PACER,
    NotionBusy,
    NotionRefused,
    Pacer,
    call,
)

PAGE_SIZE = 100
__all__ = ["MIN_INTERVAL", "PACER", "NotionBusy", "NotionRefused", "Pacer"]


@dataclass(frozen=True)
class FoundPage:
    id: str
    url: str
    values: dict[str, Any]


def _plain(prop: Any) -> Any:
    """Valeur simple d'une propriété Notion (texte, nombre, date, lien…)."""
    if not isinstance(prop, dict):
        return None
    kind = prop.get("type")
    value = prop.get(kind) if isinstance(kind, str) else None
    if kind in ("title", "rich_text"):
        parts = value if isinstance(value, list) else []
        text = "".join(str(p.get("plain_text", "")) for p in parts if isinstance(p, dict))
        return text or None
    if kind == "date":
        return value.get("start") if isinstance(value, dict) else None
    return value if isinstance(value, (str, int, float)) else None


def _page(data: Any) -> FoundPage | None:
    if not isinstance(data, dict) or not isinstance(data.get("id"), str):
        return None
    raw = data.get("properties")
    props: dict[str, Any] = raw if isinstance(raw, dict) else {}
    values = {name: _plain(p) for name, p in props.items()}
    return FoundPage(data["id"], str(data.get("url") or ""), values)


def _query(client: httpx.Client, token: str, db: str, body: dict[str, Any]) -> dict[str, Any]:
    return call(client, "POST", f"/databases/{db}/query", token, body)


def find_page(
    client: httpx.Client, token: str, db: str, app_id: str, siren: str | None
) -> FoundPage | None:
    """Doublon (C69) : par « ID app », puis par SIREN."""
    for prop, value in (("ID app", app_id), ("SIREN", siren)):
        if value:
            body = {"filter": {"property": prop, "rich_text": {"equals": value}}, "page_size": 1}
            results = _query(client, token, db, body).get("results")
            found = _page(results[0]) if isinstance(results, list) and results else None
            if found:
                return found
    return None


def create_page(
    client: httpx.Client, token: str, db: str, props: dict[str, Any]
) -> tuple[str, str]:
    body = {"parent": {"database_id": db}, "properties": props}
    page = _page(call(client, "POST", "/pages", token, body))
    if page is None:
        raise NotionBusy
    return page.id, page.url


def update_page(client: httpx.Client, token: str, page_id: str, props: dict[str, Any]) -> str:
    page = _page(call(client, "PATCH", f"/pages/{page_id}", token, {"properties": props}))
    return page.url if page else ""


def index_pages(
    client: httpx.Client, token: str, db: str, cursor: str | None
) -> tuple[list[tuple[str | None, str | None, str | None, str | None]], str | None]:
    """Une page de la base (100 fiches) : (ID app, SIREN, Entreprise, Ville) ; curseur suivant."""
    body: dict[str, Any] = {"page_size": PAGE_SIZE, **({"start_cursor": cursor} if cursor else {})}
    data = _query(client, token, db, body)
    pages = [p for raw in data.get("results") or [] if (p := _page(raw))]
    entries = [(p.values.get("ID app"), p.values.get("SIREN"), p.values.get("Entreprise"),
                p.values.get("Ville")) for p in pages]  # fmt: skip
    following = data.get("next_cursor") if data.get("has_more") else None
    return entries, following if isinstance(following, str) else None
