"""Écran « Exporter » : relecture des intéressés avant l'envoi vers Notion, bilan (C67, C74)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.crm_export import export_report, queue_export
from prospection.application.crm_target import notion_target
from prospection.application.prospect_listing import prospect_list
from prospection.config import Settings
from prospection.domain.call_status import INTERESTED
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import get_box, get_engine, get_now, get_settings, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/exporter", dependencies=[Depends(require_session)])


@router.get("", response_class=HTMLResponse)
def export_page(
    request: Request, engine: Engine = Depends(get_engine), box: SecretBox = Depends(get_box),  # noqa: B008
    now: datetime = Depends(get_now), settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    listing = prospect_list(engine, INTERESTED, "", "score", now, settings.timezone)
    context = {
        "tab": "prospects", "rows": listing.rows, "summaries": listing.summaries,
        "ready": notion_target(engine, box) is not None, "report": export_report(engine),
    }  # fmt: skip
    return templates.TemplateResponse(request, "exporter.html", context)


@router.post("")
def export_selected(
    ids: list[int] = Form(default=[]),  # noqa: B008
    engine: Engine = Depends(get_engine), box: SecretBox = Depends(get_box),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:  # fmt: skip
    """L'envoi part seulement ici, sur les prospects cochés et encore intéressés (C67)."""
    if notion_target(engine, box) is not None:
        allowed = {r.id for r in prospect_list(engine, INTERESTED, "", "trouves").rows}
        queue_export(engine, [i for i in ids[:500] if i in allowed], now)
    return RedirectResponse("/exporter", status_code=303)
