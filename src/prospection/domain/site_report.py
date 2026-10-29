"""Rapport sur le site d'un établissement : d'où il vient, ce qu'il vaut (C46 à C52)."""

from dataclasses import dataclass
from typing import Literal

from prospection.domain.page_speed import PageSpeed
from prospection.domain.site_audit import Audit
from prospection.domain.site_contacts import Contacts
from prospection.domain.site_seo import LocalSeo

Origin = Literal["fiche Google", "retrouvé", "aucun"]


@dataclass(frozen=True)
class SiteReport:
    origin: Origin
    url: str | None = None  # site adopté (fiche Google, ou retrouvé et confirmé)
    probable: str | None = None  # même nom, homonyme possible : à confirmer, jamais adopté
    problem: str | None = None  # site injoignable, refusé, trop lent…
    audit: Audit | None = None
    seo: LocalSeo | None = None
    contacts: Contacts | None = None
    parked: bool = False  # page « en construction » de l'hébergeur : pas de vrai site
    speed: PageSpeed | None = None  # vitesse mobile mesurée par Google (tâche de fond, C126)
