"""Erreurs remontées automatiquement à Sentry (C100), offre gratuite, seulement si SENTRY_DSN
est défini. Rien de personnel ni de secret ne part : ni requête (en-têtes, cookies, corps,
adresse), ni utilisateur, ni variables locales, ni fil d'événements, ni valeurs SQL."""

from typing import Any

import sentry_sdk

_CUT = ("\n", "DETAIL:", "Key (", "[SQL:", "[parameters:")


def _short(text: str) -> str:
    """Première ligne seulement : le DETAIL de PostgreSQL cite la ligne fautive (nom,
    téléphone…), les valeurs SQL aussi."""
    for marker in _CUT:
        text = text.split(marker, 1)[0]
    return text.strip()[:300]


def scrub(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    for key in ("request", "user", "server_name", "breadcrumbs", "extra"):
        event.pop(key, None)
    for exception in event.get("exception", {}).get("values", []):
        if isinstance(exception.get("value"), str):
            exception["value"] = _short(exception["value"])
        for frame in exception.get("stacktrace", {}).get("frames", []):
            frame.pop("vars", None)
    message = event.get("logentry") or {}
    for key in ("message", "formatted"):
        if isinstance(message.get(key), str):
            message[key] = _short(message[key])
    message.pop("params", None)
    return event


def start_monitoring(dsn: str | None, component: str) -> bool:
    """Vrai si les erreurs sont remontées ; `component` : app ou worker."""
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn, send_default_pii=False, include_local_variables=False, max_breadcrumbs=0,
        traces_sample_rate=0.0, before_send=scrub,  # type: ignore[arg-type]
        server_name=component,
    )  # fmt: skip
    return True
