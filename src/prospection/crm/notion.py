"""API officielle de Notion (version épinglée)."""

from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.key_check import KeyCheck, no_answer, unexpected
from prospection.domain.services import Service
from prospection.http_client import json_object, send

API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
LABEL = Service.NOTION.label


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION}


def check_notion_token(client: httpx.Client, token: str) -> KeyCheck:
    """Test gratuit : qui est l'intégration ?"""
    response = send(client, "GET", f"{API_URL}/users/me", LABEL, headers=headers(token))
    if isinstance(response, KeyCheck):
        return response
    if response.status_code == 401:
        return KeyCheck(
            False, "Jeton refusé par Notion : copiez le « secret » de votre intégration."
        )
    body = json_object(response)
    if response.status_code == 200 and body is not None and body.get("object") == "user":
        return KeyCheck(True, "Jeton Notion valide.")
    return unexpected(LABEL)


class NotionUnavailable(Exception):
    """Notion ne répond pas comme prévu ; le message dit quoi faire."""


@dataclass(frozen=True)
class NotionDatabase:
    id: str
    title: str


class _TitlePart(BaseModel):
    plain_text: str


class _Database(BaseModel):
    id: str
    title: list[_TitlePart]


class _SearchResult(BaseModel):
    results: list[_Database]


def list_notion_databases(client: httpx.Client, token: str) -> list[NotionDatabase]:
    """Bases partagées avec l'intégration, triées par titre (C06)."""
    body = {"filter": {"property": "object", "value": "database"}}
    response = send(client, "POST", f"{API_URL}/search", LABEL, headers=headers(token), json=body)
    if isinstance(response, KeyCheck):
        raise NotionUnavailable(no_answer(LABEL).message)
    if response.status_code == 401:
        raise NotionUnavailable(
            "Jeton refusé par Notion : copiez le « secret » de votre intégration."
        )
    data = json_object(response)
    try:
        if response.status_code != 200 or data is None:
            raise ValueError
        parsed = _SearchResult.model_validate(data)
    except (ValueError, ValidationError):
        raise NotionUnavailable(unexpected(LABEL).message) from None
    databases = [
        NotionDatabase(db.id, "".join(part.plain_text for part in db.title) or "Sans titre")
        for db in parsed.results
    ]
    return sorted(databases, key=lambda db: db.title.casefold())
