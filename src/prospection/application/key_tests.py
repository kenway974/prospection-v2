"""Tester une clé enregistrée auprès de son service et garder le résultat (C03)."""

from collections.abc import Callable
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.crm.notion import check_notion_token
from prospection.domain.key_check import KeyCheck
from prospection.domain.services import Service
from prospection.sources.google_places import check_google_key
from prospection.sources.insee import check_insee_key
from prospection.storage.api_keys import load_key, record_test
from prospection.storage.secret_box import SecretBox

CHECKERS: dict[Service, Callable[[httpx.Client, str], KeyCheck]] = {
    Service.GOOGLE: check_google_key,
    Service.NOTION: check_notion_token,
    Service.INSEE: check_insee_key,
}


def run_key_test(
    engine: Engine, box: SecretBox, service: Service, client: httpx.Client, now: datetime
) -> KeyCheck:
    with engine.connect() as conn:
        stored = load_key(conn, service)
    if stored is None:
        return KeyCheck(False, "Aucune clé enregistrée.")
    key = read_key(engine, box, service)
    result = (
        KeyCheck(False, "Clé illisible : saisissez-la à nouveau.")
        if key is None
        else CHECKERS[service](client, key)
    )
    with engine.begin() as conn:
        record_test(conn, service, now, result.ok, result.message)
    return result
