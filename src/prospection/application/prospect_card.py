"""Liste des prospects et fiche d'appel avec sa place dans la file (C61, C109, C120)."""

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine

from prospection.domain.place import web_link
from prospection.storage.call_tracking import Action, Note, notes, open_action
from prospection.storage.prospect_list import (
    ProspectRow,
    load_prospect,
    prospect_rows,
    save_session,
    status_counts,
)


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
    position: int | None
    total: int
    previous_id: int | None
    next_id: int | None


def prospect_list(engine: Engine, status: str | None, query: str) -> ProspectList:
    with engine.connect() as conn:
        return ProspectList(prospect_rows(conn, status, query), status_counts(conn))


def tel_link(phone: object) -> str | None:
    """Numéro pour un lien `tel:` : chiffres et « + » seulement (texte venu de Google)."""
    digits = re.sub(r"[^\d+]", "", phone) if isinstance(phone, str) else ""
    return digits[:20] or None


def card(
    engine: Engine, prospect_id: int, status: str | None, query: str, now: datetime,
    remember: bool = True,
) -> Card:  # fmt: skip
    """La fiche dans la file filtrée ; à l'affichage, la session est mémorisée (C109)."""
    with engine.begin() as conn:
        prospect = load_prospect(conn, prospect_id)
        if prospect is None:
            raise UnknownProspect(prospect_id)
        queue = [r.id for r in prospect_rows(conn, status, query)]
        if remember:
            save_session(conn, status, query, prospect_id, now)
        found_notes, action = notes(conn, prospect_id), open_action(conn, prospect_id)
    index = queue.index(prospect_id) if prospect_id in queue else None
    return Card(
        prospect, tel_link(prospect.data.get("phone")), web_link(prospect.data.get("website")),
        web_link(prospect.data.get("maps_url")), found_notes, action,
        None if index is None else index + 1, len(queue),
        queue[index - 1] if index else None,
        queue[index + 1] if index is not None and index + 1 < len(queue) else None,
    )  # fmt: skip
