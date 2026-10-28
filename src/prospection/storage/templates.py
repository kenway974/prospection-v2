"""Modèles de campagne (C18)."""

from dataclasses import dataclass

from sqlalchemy import Connection, func, insert, select

from prospection.domain.campaign_request import CampaignRequest
from prospection.storage.campaign_codec import decode_request, encode_request
from prospection.storage.schema_campaigns import campaign_templates


@dataclass(frozen=True)
class Template:
    name: str
    request: CampaignRequest


def clean_name(name: str) -> str:
    return name.strip()[:100]


def template_exists(conn: Connection, name: str) -> bool:
    """Majuscules ignorées : « Cuisinistes 974 » et « cuisinistes 974 » sont le même modèle."""
    t = campaign_templates.c
    wanted = func.lower(clean_name(name))
    return conn.execute(select(t.name).where(func.lower(t.name) == wanted)).first() is not None


def save_template(conn: Connection, name: str, request: CampaignRequest) -> None:
    """Jamais d'écrasement : vérifier d'abord avec template_exists."""
    clean = clean_name(name)
    if not clean:
        raise ValueError("Nom de modèle vide")
    conn.execute(
        insert(campaign_templates).values(name=clean, request_json=encode_request(request))
    )


def list_templates(conn: Connection) -> list[Template]:
    t = campaign_templates.c
    rows = conn.execute(select(t.name, t.request_json).order_by(t.name))
    return [Template(r.name, decode_request(r.request_json)) for r in rows]


def load_template(conn: Connection, name: str) -> Template | None:
    t = campaign_templates.c
    row = conn.execute(select(t.name, t.request_json).where(t.name == name)).first()
    return Template(row.name, decode_request(row.request_json)) if row else None
