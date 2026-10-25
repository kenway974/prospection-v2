"""Modèles de campagne (C18)."""

from dataclasses import dataclass

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from prospection.domain.campaign_request import CampaignRequest
from prospection.storage.campaign_codec import decode_request, encode_request
from prospection.storage.schema_campaigns import campaign_templates


@dataclass(frozen=True)
class Template:
    name: str
    request: CampaignRequest


def save_template(conn: Connection, name: str, request: CampaignRequest) -> None:
    clean = name.strip()[:100]
    if not clean:
        raise ValueError("Nom de modèle vide")
    data = encode_request(request)
    statement = insert(campaign_templates).values(name=clean, request_json=data)
    conn.execute(
        statement.on_conflict_do_update(index_elements=["name"], set_={"request_json": data})
    )


def list_templates(conn: Connection) -> list[Template]:
    t = campaign_templates.c
    rows = conn.execute(select(t.name, t.request_json).order_by(t.name))
    return [Template(r.name, decode_request(r.request_json)) for r in rows]
