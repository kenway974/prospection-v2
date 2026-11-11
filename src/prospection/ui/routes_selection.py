"""Prospects cochés dans la liste : confirmation, puis suppression en une fois (C129).

La sélection part en POST : des centaines d'identifiants ne tiennent pas dans une adresse."""

from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.mail_batch import batch_preview, queue_batch
from prospection.application.mail_queue_view import current_limit
from prospection.application.prospect_selection import MAX_SELECTION, delete_selection, selected
from prospection.application.site_reaudit import request_reaudits
from prospection.storage.secret_box import SecretBox
from prospection.ui.call_views import list_scope, scope_params
from prospection.ui.deps import get_box, get_engine, get_now, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/prospects/selection", dependencies=[Depends(require_session)])
ENGINE, BOX, NOW = Depends(get_engine), Depends(get_box), Depends(get_now)
IDS = Form([])
ORIGIN, CAMPAIGN = Form("", max_length=20), Form("", max_length=20)


def _back(origine: str, campagne: str, deleted: int = 0, queued: int = 0, audits: int = 0) -> str:
    """Retour au même onglet et à la même campagne que la liste d'où l'on vient."""
    here = scope_params(list_scope(origine, campagne))
    params = {"supprime": str(deleted)} if deleted else {}
    params |= {"en_file": str(queued)} if queued else {}
    params |= {"audit": str(audits)} if audits else {}
    params |= {k: v for k, v in here.items() if v and (k, v) != ("origine", "appel")}
    return "/prospects" + (f"?{urlencode(params)}" if params else "")


@router.post("", response_class=HTMLResponse)
def confirm_page(
    request: Request, id: list[int] = IDS, origine: str = ORIGIN, campagne: str = CAMPAIGN,
    engine: Engine = ENGINE,
) -> Response:  # fmt: skip
    chosen = selected(engine, id)
    if not chosen:
        return RedirectResponse(_back(origine, campagne), status_code=303)
    context = {
        "tab": "prospects", "chosen": chosen, "origine": origine, "campagne": campagne,
        "back": _back(origine, campagne), "limit": MAX_SELECTION,
        "cut": len(set(id)) > MAX_SELECTION,
    }  # fmt: skip
    return templates.TemplateResponse(request, "supprimer_selection.html", context)


@router.post("/supprimer")
def delete(
    id: list[int] = IDS, jamais: str = Form("", max_length=5), origine: str = ORIGIN,
    campagne: str = CAMPAIGN, engine: Engine = ENGINE,
) -> Response:  # fmt: skip
    count = delete_selection(engine, id, forever=jamais == "on")
    return RedirectResponse(_back(origine, campagne, count), status_code=303)


@router.post("/mail", response_class=HTMLResponse)
def mail_confirm(
    request: Request, id: list[int] = IDS, origine: str = ORIGIN, campagne: str = CAMPAIGN,
    engine: Engine = ENGINE, box: SecretBox = BOX,
) -> Response:  # fmt: skip
    """C168 : ce qui partira, ce qui est écarté et pourquoi."""
    preview = batch_preview(engine, box, id)
    if not preview.rows:
        return RedirectResponse(_back(origine, campagne), status_code=303)
    context = {"tab": "prospects", "preview": preview, "origine": origine, "campagne": campagne,
               "back": _back(origine, campagne), "limit": current_limit(engine)}  # fmt: skip
    return templates.TemplateResponse(request, "mail_selection.html", context)


@router.post("/mail/envoyer")
def mail_queue(
    id: list[int] = IDS, origine: str = ORIGIN, campagne: str = CAMPAIGN,
    engine: Engine = ENGINE, box: SecretBox = BOX, now: datetime = NOW,
) -> Response:  # fmt: skip
    """C168 : en file pour la tâche de fond ; rien ne part d'ici."""
    count = queue_batch(engine, box, id, now)
    return RedirectResponse(_back(origine, campagne, queued=count), status_code=303)


@router.post("/audit")
def reaudit_selection(
    id: list[int] = IDS, origine: str = ORIGIN, campagne: str = CAMPAIGN,
    engine: Engine = ENGINE, now: datetime = NOW,
) -> Response:  # fmt: skip
    """C185 : nouvel audit des prospects cochés, fait par la tâche de fond."""
    count = request_reaudits(engine, id, now)
    return RedirectResponse(_back(origine, campagne, audits=count), status_code=303)
