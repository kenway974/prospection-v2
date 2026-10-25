"""API officielle de Notion (version épinglée)."""

import httpx

from prospection.domain.key_check import KeyCheck, unexpected
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
