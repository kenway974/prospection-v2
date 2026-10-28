"""Outils de test des campagnes : faux Google qui sert des pages d'établissements."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from cryptography.fernet import Fernet

from prospection.domain.campaign_request import CampaignRequest, CityZone
from prospection.domain.criteria import Criteria
from prospection.domain.google_cost import Pricing
from prospection.storage.secret_box import SecretBox

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
BOX = SecretBox(Fernet.generate_key().decode())
PRICING = Pricing(free_per_month=1000, usd_per_1000=Decimal("35"), eur_per_usd=Decimal("0.93"))
LYON = CityZone("Lyon", "69123", 45.76, 4.83)
TABLES = (
    "campaigns, campaign_steps, prospects, google_usage, campaign_events, api_keys, mail_domains, "
    "alerts, campaign_schedules, campaign_templates"
)


def request(target: int = 3, trades: tuple[str, ...] = ("cuisiniste",)) -> CampaignRequest:
    return CampaignRequest("Test", trades, (LYON,), target, Criteria(phone="any"), False)


def api_place(n: int, reviews: int = 2, name: str | None = None) -> dict[str, object]:
    return {
        "id": f"place-{n}",
        "displayName": {"text": name or f"Cuisines Martin {n}"},
        "location": {"latitude": 45.76, "longitude": 4.83},
        "types": ["furniture_store"],
        "userRatingCount": reviews,
    }


def pages(*batches: list[dict[str, object]]) -> Callable[[httpx.Request], httpx.Response]:
    """Sert les pages dans l'ordre, chacune avec un jeton vers la suivante."""
    served = iter(range(len(batches)))

    def handler(request: httpx.Request) -> httpx.Response:
        index = next(served, None)
        if index is None:
            return httpx.Response(200, json={"places": []})
        body: dict[str, object] = {"places": batches[index]}
        if index + 1 < len(batches):
            body["nextPageToken"] = f"tok{index + 1}"
        return httpx.Response(200, json=body)

    return handler
