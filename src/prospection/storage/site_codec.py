"""Rapport du site <-> JSON (stockage)."""

import logging
from dataclasses import asdict
from typing import Any

from prospection.domain.page_speed import PageSpeed
from prospection.domain.site_audit import Audit
from prospection.domain.site_codes import legacy_codes
from prospection.domain.site_contacts import Contacts
from prospection.domain.site_report import SiteReport
from prospection.domain.site_seo import LocalSeo

logger = logging.getLogger(__name__)


def encode_site(report: SiteReport) -> dict[str, Any]:
    return asdict(report)


def decode_site(data: dict[str, Any]) -> SiteReport | None:
    """Rapport relu ; ancien ou incomplet : None (« pas encore analysé »), jamais d'erreur."""
    try:
        return _decode(data)
    except (KeyError, TypeError, ValueError):
        logger.warning("Rapport de site illisible : ignoré")
        return None


def _decode(data: dict[str, Any]) -> SiteReport:
    audit, seo, contacts = data.get("audit"), data.get("seo"), data.get("contacts")
    return SiteReport(
        data["origin"], data.get("url"), data.get("probable"), data.get("problem"),
        _audit(audit) if audit else None,
        LocalSeo(seo["trade"], seo["city"], tuple(seo["problems"])) if seo else None,
        Contacts(*(tuple(contacts[k]) for k in ("emails", "phones", "social")))
        if contacts else None,
        bool(data.get("parked", False)),
        decode_speed(data["speed"]) if data.get("speed") else None,
        _unconfirmed(data),

    )  # fmt: skip


def _unconfirmed(data: dict[str, Any]) -> bool:
    """Rapport d'avant C173 : le site de la fiche Google n'a jamais été vérifié, il est donc
    à vérifier (refaire l'audit) plutôt que supposé être celui de l'entreprise."""
    if "unconfirmed" in data:
        return bool(data["unconfirmed"])
    return data.get("origin") == "fiche Google" and bool(data.get("audit"))


def _audit(data: dict[str, Any]) -> Audit:
    problems = tuple(data["problems"])
    codes = tuple(data["codes"]) if "codes" in data else legacy_codes(problems)
    return Audit(**{**data, "problems": problems, "codes": codes})


def decode_speed(data: dict[str, Any]) -> PageSpeed:
    return PageSpeed(int(data["score"]), data.get("display_ms"), tuple(data.get("issues", ())))
