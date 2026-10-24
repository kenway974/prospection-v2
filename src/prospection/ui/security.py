"""Sécurité HTTP : en-têtes, HTTPS uniquement (C84), origine des actions."""

from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse, Response

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; manifest-src 'self'; worker-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(self)",
}
HEALTH_PATH = "/sante"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CROSS_SITE_MESSAGE = "Action refusée : elle ne vient pas de l'app. Rechargez la page et réessayez."


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response


class HttpsOnlyMiddleware(BaseHTTPMiddleware):
    """Derrière le proxy de Railway, redirige toute requête arrivée en HTTP."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.headers.get("x-forwarded-proto") == "http" and (request.url.path != HEALTH_PATH):
            return RedirectResponse(str(request.url.replace(scheme="https")), status_code=308)
        return await call_next(request)


class SameOriginMiddleware(BaseHTTPMiddleware):
    """Refuse les actions (POST…) qui ne viennent pas d'une page de l'app."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in UNSAFE_METHODS and not _same_origin(request):
            return PlainTextResponse(CROSS_SITE_MESSAGE, status_code=403)
        return await call_next(request)


def _same_origin(request: Request) -> bool:
    source = request.headers.get("origin") or request.headers.get("referer")
    host = request.headers.get("host")
    return bool(source and host) and urlsplit(source).netloc == host
