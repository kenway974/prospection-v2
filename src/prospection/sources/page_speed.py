"""Google PageSpeed Insights (API officielle, gratuite) : vitesse d'un site sur mobile.
C'est Google qui visite le site, pas notre serveur. Réponse validée ; seules la note, le
temps d'affichage et les audits à améliorer sont gardés."""

from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from prospection.domain.page_speed import ISSUE_LABELS, PageSpeed

API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
TIMEOUT = 90.0  # une analyse prend souvent 10 à 40 s
FAILING = 0.9  # audit sous ce score : à améliorer


class SpeedBusy(Exception):
    """Google trop sollicité ou injoignable : nouvel essai plus tard."""


class SpeedRefused(Exception):
    """Clé refusée ou API non activée ; le message dit quoi faire."""


class _Audit(BaseModel):
    score: float | None = None
    numericValue: float | None = None
    details: dict[str, Any] | None = None


class _Category(BaseModel):
    score: float | None = None


class _Lighthouse(BaseModel):
    categories: dict[str, _Category]
    audits: dict[str, _Audit] = {}


class _Answer(BaseModel):
    lighthouseResult: _Lighthouse


def _saving(audit: _Audit) -> float:
    value = (audit.details or {}).get("overallSavingsMs")
    return float(value) if isinstance(value, int | float) else 0.0


def _parse(body: Any) -> PageSpeed | None:
    try:
        result = _Answer.model_validate(body).lighthouseResult
    except ValidationError:
        return None
    performance = result.categories.get("performance")
    if performance is None or performance.score is None:
        return None
    failing = [(name, a) for name, a in result.audits.items()
               if name in ISSUE_LABELS and a.score is not None and a.score < FAILING]  # fmt: skip
    failing.sort(key=lambda item: _saving(item[1]), reverse=True)
    lcp = result.audits.get("largest-contentful-paint")
    display = round(lcp.numericValue) if lcp and lcp.numericValue is not None else None
    return PageSpeed(round(performance.score * 100), display, tuple(n for n, _ in failing))


def page_speed(client: httpx.Client, key: str, url: str) -> PageSpeed | None:
    """Mesure mobile du site ; None si Google ne peut pas l'analyser (site injoignable)."""
    params = {"url": url, "strategy": "mobile", "category": "performance", "locale": "fr",
              "key": key}  # fmt: skip
    try:
        response = client.get(API_URL, params=params, timeout=TIMEOUT)
    except httpx.HTTPError:
        raise SpeedBusy from None
    if response.status_code == 429 or response.status_code >= 500:
        raise SpeedBusy
    if response.status_code in (401, 403):
        raise SpeedRefused(
            "PageSpeed refusé : activez « PageSpeed Insights API » dans Google Cloud et "
            "autorisez-la sur la clé Google."
        )
    if response.status_code != 200:
        return None  # 400 : Google n'a pas pu charger le site
    try:
        return _parse(response.json())
    except ValueError:
        raise SpeedBusy from None
