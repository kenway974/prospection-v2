"""Routes publiques : sonde de santé (Railway) et service worker (C116)."""

from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse

from prospection.ui.paths import STATIC_DIR

router = APIRouter()


@router.get("/sante", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@router.get("/service-worker.js")
def service_worker() -> FileResponse:
    headers = {"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"}
    return FileResponse(
        STATIC_DIR / "service-worker.js", media_type="text/javascript", headers=headers
    )
