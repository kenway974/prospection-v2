"""Rapport du site <-> JSON (stockage)."""

from dataclasses import asdict
from typing import Any

from prospection.domain.site_audit import Audit
from prospection.domain.site_contacts import Contacts
from prospection.domain.site_report import SiteReport
from prospection.domain.site_seo import LocalSeo


def encode_site(report: SiteReport) -> dict[str, Any]:
    return asdict(report)


def decode_site(data: dict[str, Any]) -> SiteReport:
    audit, seo, contacts = data.get("audit"), data.get("seo"), data.get("contacts")
    return SiteReport(
        data["origin"], data.get("url"), data.get("probable"), data.get("problem"),
        Audit(**{**audit, "problems": tuple(audit["problems"])}) if audit else None,
        LocalSeo(seo["trade"], seo["city"], tuple(seo["problems"])) if seo else None,
        Contacts(*(tuple(contacts[k]) for k in ("emails", "phones", "social")))
        if contacts else None,
    )  # fmt: skip
