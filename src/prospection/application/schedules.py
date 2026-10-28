"""Campagnes programmées chaque semaine à partir d'un modèle (C77) ; échec en alerte (C98)."""

import dataclasses
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Engine

from prospection.application.campaigns import create_campaign_in
from prospection.domain.schedule import WEEKDAYS, next_run
from prospection.storage import schedules as store
from prospection.storage.alerts import add_alert
from prospection.storage.templates import Template, list_templates, load_template

logger = logging.getLogger(__name__)


class InvalidSchedule(ValueError):
    """Programmation incomplète ; le message dit quoi faire."""


def schedule_screen(engine: Engine) -> tuple[list[store.Schedule], list[Template]]:
    with engine.connect() as conn:
        return store.list_schedules(conn), list_templates(conn)


def _number(text: str) -> int:
    """Chiffres 0-9 seulement (« ² » ou « ٣ » refusés) ; -1 si autre chose."""
    clean = text.strip()
    return int(clean) if clean.isascii() and clean.isdigit() else -1


def add_schedule(
    engine: Engine, template_name: str, weekday: str, hour: str, now: datetime, timezone: str
) -> None:
    """Une même programmation (modèle, jour, heure) n'est enregistrée qu'une fois."""
    day, at = _number(weekday), _number(hour)
    if not 0 <= day < len(WEEKDAYS):
        raise InvalidSchedule("Choisissez un jour.")
    if not 0 <= at <= 23:
        raise InvalidSchedule("Choisissez une heure entre 0 et 23.")
    with engine.begin() as conn:
        if load_template(conn, template_name) is None:
            raise InvalidSchedule("Choisissez un modèle (enregistrez-en un depuis Recherche).")
        first = next_run(now.astimezone(ZoneInfo(timezone)), day, at)
        store.add_schedule(conn, template_name, day, at, first, now)


def delete_schedule(engine: Engine, schedule_id: int) -> None:
    with engine.begin() as conn:
        store.delete_schedule(conn, schedule_id)


def run_due_schedule(engine: Engine, now: datetime, timezone: str) -> bool:
    """Lance la plus en retard des programmations échues ; vrai si une l'était. La campagne
    naît dans la même transaction que le prochain passage : une coupure ne saute aucune
    semaine, et un modèle illisible n'est retenté que la semaine suivante (alerte C98)."""
    local = now.astimezone(ZoneInfo(timezone))
    with engine.begin() as conn:
        due = store.claim_due(conn, now)
        if due is None:
            return False
        store.set_next_run(conn, due.id, next_run(local, due.weekday, due.hour))
        try:
            with conn.begin_nested():
                template = load_template(conn, due.template_name)
                if template is not None:  # sinon supprimé : la programmation l'est aussi
                    name = f"{template.name} · {local:%d/%m}"
                    request = dataclasses.replace(template.request, name=name)
                    create_campaign_in(conn, request, now, schedule_id=due.id)
        except Exception:
            logger.exception("Campagne programmée %s non lancée", due.id)
            message = f"Campagne programmée « {due.template_name} » non lancée : ouvrez le modèle."
            add_alert(conn, f"lancement:{due.id}:{now:%Y-%m-%d}", "echec", message,
                      "/programmes", now)  # fmt: skip
    return True
