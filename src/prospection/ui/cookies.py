"""Pose et retrait du cookie de session."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from prospection.ui.session import COOKIE_NAME, MAX_AGE


def set_session_cookie(response: Response, value: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        value,
        max_age=int(MAX_AGE.total_seconds()),
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


class SessionRefreshMiddleware(BaseHTTPMiddleware):
    """Réémet le cookie quand require_session a demandé son renouvellement."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        new_value = getattr(request.state, "new_session", None)
        if new_value:
            set_session_cookie(response, new_value)
        return response
