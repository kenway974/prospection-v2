"""Liste des prospects, session d'appel et fiche (C61, C103, C109, C120)."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from prospection.domain.call_status import proposed_action
from prospection.domain.company_card import registry_lines
from prospection.domain.place import web_link
from prospection.domain.text import without_controls
from prospection.storage import prospect_list as store
from prospection.storage.call_tracking import Action, Note, notes, open_action
from prospection.storage.prospect_list import ProspectRow


class UnknownProspect(LookupError):
    """Aucun prospect qualifié avec cet identifiant."""


@dataclass(frozen=True)
class ProspectList:
    rows: list[ProspectRow]
    counts: dict[str, int]


@dataclass(frozen=True)
class Card:
    prospect: ProspectRow
    tel: str | None
    website: str | None
    maps_url: str | None
    notes: list[Note]
    action: Action | None
    proposal: tuple[str, date] | None  # « Rappeler demain », préparé mais pas enregistré
    company_lines: list[tuple[str, str]]  # bloc « L'entreprise » (registre)
    position: int | None
    total: int
    previous_id: int | None
    next_id: int | None


def clean_query(query: str) -> str:
    return without_controls(query)[:100]


def prospect_list(engine: Engine, status: str | None, query: str, sort: str) -> ProspectList:
    with engine.connect() as conn:
        rows = store.prospect_rows(conn, status, clean_query(query), sort)
        return ProspectList(rows, store.status_counts(conn, clean_query(query)))


def start_session(
    engine: Engine, status: str | None, query: str, sort: str, now: datetime
) -> int | None:
    """Fige la file affichée et renvoie le premier prospect à appeler (C109)."""
    with engine.begin() as conn:
        queue = store.prospect_ids(conn, status, clean_query(query), sort)
        store.start_session(conn, queue, now)
    return queue[0] if queue else None


def tel_link(phone: object) -> str | None:
    """Numéro pour un lien `tel:` : chiffres et « + » seulement (texte venu de Google)."""
    digits = re.sub(r"[^\d+]", "", phone) if isinstance(phone, str) else ""
    return digits[:20] or None


def _neighbours(queue: list[int], prospect_id: int) -> tuple[int | None, int | None, int | None]:
    if prospect_id not in queue:
        return None, None, None
    i = queue.index(prospect_id)
    return i + 1, queue[i - 1] if i else None, queue[i + 1] if i + 1 < len(queue) else None


def card(
    engine: Engine, prospect_id: int, now: datetime, timezone: str, in_session: bool = False
) -> Card:
    """Ouverte depuis la session, la fiche y prend sa place et devient le point de reprise."""
    with engine.begin() as conn:
        prospect = store.load_prospect(conn, prospect_id)
        if prospect is None:
            raise UnknownProspect(prospect_id)
        session = store.load_session(conn) if in_session else None
        queue = session.queue if session and prospect_id in session.queue else []
        if queue:
            store.move_session(conn, prospect_id, now)
        found_notes, action = notes(conn, prospect_id), open_action(conn, prospect_id)
    today = now.astimezone(ZoneInfo(timezone)).date()
    proposal = None if action else proposed_action(prospect.status, today)
    position, previous_id, next_id = _neighbours(queue, prospect_id)
    return Card(
        prospect, tel_link(prospect.data.get("phone")), web_link(prospect.data.get("website")),
        web_link(prospect.data.get("maps_url")), found_notes, action, proposal,
        registry_lines(prospect.company, prospect.registry_status), position,
        len(queue), previous_id, next_id,
    )  # fmt: skip
