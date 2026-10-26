"""Saisies de la fiche d'appel et écran Aujourd'hui (C102 à C107, C109).

Chaque saisie est enregistrée tout de suite ; une saisie refusée lève InvalidInput avec le
champ et le message à afficher, sans rien changer (C106).
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, Engine

from prospection.application.prospect_card import UnknownProspect
from prospection.domain.agenda import Agenda, agenda
from prospection.domain.call_status import (
    ACTION_KINDS,
    InvalidStatus,
    check_result,
    proposed_action,
)
from prospection.domain.contact import InvalidContact, clean_contact
from prospection.storage import call_tracking as store
from prospection.storage.prospect_list import load_prospect, load_session, prospect_rows

MAX_NOTE = 2000


class InvalidInput(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field, self.message = field, message


@dataclass(frozen=True)
class Resume:
    prospect_id: int
    name: str
    position: int
    total: int


@dataclass(frozen=True)
class TodayScreen:
    agenda: Agenda
    resume: Resume | None


def _country(conn: Connection, prospect_id: int) -> str:
    prospect = load_prospect(conn, prospect_id)
    if prospect is None:
        raise UnknownProspect(prospect_id)
    return str(prospect.data.get("country") or "FR")


def record_result(
    engine: Engine, prospect_id: int, status: str, now: datetime, timezone: str
) -> None:
    """Résultat d'appel ; « à rappeler » ou « messagerie » prévoient Rappeler demain."""
    try:
        check_result(status)
    except InvalidStatus:
        raise InvalidInput("status", "Choisissez un résultat dans la liste.") from None
    with engine.begin() as conn:
        _country(conn, prospect_id)
        store.set_call_status(conn, prospect_id, status, now)
        proposal = proposed_action(status, now.astimezone(ZoneInfo(timezone)).date())
        if proposal and store.open_action(conn, prospect_id) is None:
            store.plan_action(conn, prospect_id, proposal[0], proposal[1], None, now)


def _parse(day: str, at: str) -> tuple[date, time | None]:
    try:
        due = date.fromisoformat(day.strip())
    except ValueError:
        raise InvalidInput("date", "Choisissez une date.") from None
    try:
        return due, time.fromisoformat(at.strip()) if at.strip() else None
    except ValueError:
        raise InvalidInput("time", "Heure invalide : écrivez-la ainsi, 14:30.") from None


def schedule(engine: Engine, prospect_id: int, kind: str, day: str, at: str, now: datetime) -> None:
    if kind not in ACTION_KINDS:
        raise InvalidInput("kind", "Choisissez une action dans la liste.")
    due, due_time = _parse(day, at)
    with engine.begin() as conn:
        _country(conn, prospect_id)
        store.plan_action(conn, prospect_id, kind, due, due_time, now)


def save_note(engine: Engine, prospect_id: int, text: str, now: datetime) -> None:
    clean = text.strip()
    if not clean:
        raise InvalidInput("note", "Écrivez la note avant de l'enregistrer.")
    if len(clean) > MAX_NOTE:
        raise InvalidInput("note", "2 000 caractères au plus : raccourcissez la note.")
    with engine.begin() as conn:
        _country(conn, prospect_id)
        store.add_note(conn, prospect_id, clean, now)


def save_contact(
    engine: Engine, prospect_id: int, name: str, mobile: str, email: str, now: datetime
) -> None:
    with engine.begin() as conn:
        try:
            contact = clean_contact(name, mobile, email, _country(conn, prospect_id))
        except InvalidContact as invalid:
            field, message = next(iter(invalid.errors.items()))
            raise InvalidInput(field, message) from None
        store.update_contact(conn, prospect_id, contact, now)


def finish_action(engine: Engine, action_id: int, now: datetime) -> None:
    with engine.begin() as conn:
        store.complete_action(conn, action_id, now)


def today_screen(engine: Engine, now: datetime, timezone: str) -> TodayScreen:
    with engine.connect() as conn:
        items, session = store.agenda_items(conn), load_session(conn)
        resume = None
        if session and session.prospect_id:
            queue = prospect_rows(conn, session.status, session.query)
            ids = [r.id for r in queue]
            if session.prospect_id in ids:
                index = ids.index(session.prospect_id)
                name = str(queue[index].data.get("name", ""))
                resume = Resume(session.prospect_id, name, index + 1, len(ids))
    return TodayScreen(agenda(items, now, timezone), resume)
