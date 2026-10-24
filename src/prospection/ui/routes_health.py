"""Sonde de santé pour Railway."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/sante", response_class=PlainTextResponse)
def health() -> str:
    return "ok"
