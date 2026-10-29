"""Prospects cochés dans la liste : confirmation, puis suppression en une fois (C129)."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.prospect_selection import delete_selection, selected
from prospection.domain.prospect_source import FIELD
from prospection.ui.deps import get_engine, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/prospects/selection", dependencies=[Depends(require_session)])
ENGINE = Depends(get_engine)


def _back(origine: str, deleted: int = 0) -> str:
    params = [f"supprime={deleted}"] if deleted else []
    params += ["origine=terrain"] if origine == FIELD else []
    return "/prospects" + ("?" + "&".join(params) if params else "")


@router.get("/supprimer", response_class=HTMLResponse)
def confirm_page(
    request: Request, id: list[int] = Query([]), origine: str = Query("", max_length=20),  # noqa: B008
    engine: Engine = ENGINE,
) -> Response:  # fmt: skip
    chosen = selected(engine, id)
    if not chosen:
        return RedirectResponse(_back(origine), status_code=303)
    context = {"tab": "prospects", "chosen": chosen, "origine": origine, "back": _back(origine)}
    return templates.TemplateResponse(request, "supprimer_selection.html", context)


@router.post("/supprimer")
def delete(
    id: list[int] = Form([]), jamais: str = Form("", max_length=5),  # noqa: B008
    origine: str = Form("", max_length=20), engine: Engine = ENGINE,
) -> Response:  # fmt: skip
    count = delete_selection(engine, id, forever=jamais == "on")
    return RedirectResponse(_back(origine, count), status_code=303)
