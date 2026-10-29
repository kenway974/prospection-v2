"""Alertes, réglage des rappels et campagnes programmées (C77, C78, C98, C108)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.alerts import dismiss, reminder_settings
from prospection.application.reminders import InvalidReminders, change_reminders
from prospection.application.schedules import (
    InvalidSchedule,
    add_schedule,
    delete_schedule,
    schedule_screen,
)
from prospection.config import Settings
from prospection.domain.schedule import WEEKDAYS
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.formatting import short_datetime
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])
ENGINE = Depends(get_engine)
NOW = Depends(get_now)
SETTINGS = Depends(get_settings)


@router.post("/alertes/{alert_id}/vu")
def seen(alert_id: int, engine: Engine = ENGINE, now: datetime = NOW) -> Response:
    dismiss(engine, now, alert_id)
    return RedirectResponse("/", status_code=303)


@router.post("/alertes/vu")
def all_seen(engine: Engine = ENGINE, now: datetime = NOW) -> Response:
    dismiss(engine, now)
    return RedirectResponse("/", status_code=303)


def _reminders(
    request: Request, engine: Engine, settings: Settings, error: str | None, code: int,
    reached: int | None = None,
) -> Response:  # fmt: skip
    minutes, hour, calm_from, calm_to = reminder_settings(engine)
    keys = settings.vapid_keys()
    context = {"tab": "", "minutes": minutes, "hour": hour, "calm_from": calm_from,
               "calm_to": calm_to, "error": error, "reached": reached,
               "vapid_public": keys.public_key if keys else None}  # fmt: skip
    return templates.TemplateResponse(request, "reglages_rappels.html", context, status_code=code)


@router.get("/reglages/rappels", response_class=HTMLResponse)
def reminders_page(
    request: Request, essai: int | None = None, engine: Engine = ENGINE,
    settings: Settings = SETTINGS,
) -> Response:  # fmt: skip
    return _reminders(request, engine, settings, None, 200, essai)


@router.post("/reglages/rappels")
def save_reminders(
    request: Request, minutes: str = Form("", max_length=5), heure: str = Form("", max_length=5),
    calme_debut: str = Form("21", max_length=5), calme_fin: str = Form("8", max_length=5),
    engine: Engine = ENGINE, settings: Settings = SETTINGS,
) -> Response:  # fmt: skip
    try:
        change_reminders(engine, minutes, heure, calme_debut, calme_fin)
    except InvalidReminders as error:
        return _reminders(request, engine, settings, str(error), 400)
    return RedirectResponse("/reglages/rappels", status_code=303)


def _schedules(
    request: Request, engine: Engine, settings: Settings, error: str | None, code: int
) -> Response:
    planned, models = schedule_screen(engine)
    rows = [(s.id, s.template_name, WEEKDAYS[s.weekday], s.hour,
             short_datetime(s.next_run_at, settings.timezone)) for s in planned]  # fmt: skip
    context = {"tab": "search", "rows": rows, "models": [m.name for m in models],
               "days": list(enumerate(WEEKDAYS)), "error": error}  # fmt: skip
    return templates.TemplateResponse(request, "programmes.html", context, status_code=code)


@router.get("/programmes", response_class=HTMLResponse)
def schedules_page(
    request: Request, engine: Engine = ENGINE, settings: Settings = SETTINGS
) -> Response:
    return _schedules(request, engine, settings, None, 200)


@router.post("/programmes")
def add_schedule_choice(
    request: Request, modele: str = Form("", max_length=100), jour: str = Form("", max_length=2),
    heure: str = Form("", max_length=2), engine: Engine = ENGINE, now: datetime = NOW,
    settings: Settings = SETTINGS,
) -> Response:  # fmt: skip
    try:
        add_schedule(engine, modele, jour, heure, now, settings.timezone)
    except InvalidSchedule as error:
        return _schedules(request, engine, settings, str(error), 400)
    return RedirectResponse("/programmes", status_code=303)


@router.post("/programmes/{schedule_id}/supprimer")
def remove_schedule(schedule_id: int, engine: Engine = ENGINE) -> Response:
    delete_schedule(engine, schedule_id)
    return RedirectResponse("/programmes", status_code=303)
