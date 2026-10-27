"""Signaux d'un prospect, tirés des données déjà gardées (fiche Google, site, registre).

Base commune du score (C57), de la raison (C58), de la confiance (C60), de la fiche
« Pour l'appel » (C110) et des indices de santé (C112). Fonction pure : la date du jour
est passée en paramètre.
"""

from dataclasses import dataclass
from datetime import date

from prospection.domain.company import Company
from prospection.domain.phones import is_mobile
from prospection.domain.place import Place
from prospection.domain.site_audit import Audit
from prospection.domain.site_report import SiteReport


@dataclass(frozen=True)
class Signals:
    place: Place
    site: SiteReport | None
    company: Company | None
    registry_status: str | None
    flags: tuple[str, ...]
    age_days: int | None  # ancienneté de l'entreprise (registre)

    @property
    def has_site(self) -> bool:
        return bool(self.place.website or (self.site and self.site.url))

    @property
    def audit(self) -> Audit | None:
        return self.site.audit if self.site else None

    @property
    def mobile(self) -> bool:
        return bool(self.place.phone and is_mobile(self.place.phone, self.place.country))


def signals_of(
    place: Place, site: SiteReport | None, company: Company | None,
    registry_status: str | None, flags: tuple[str, ...], today: date,
) -> Signals:  # fmt: skip
    created = company.created if company else None
    age = (today - created).days if created and created <= today else None
    return Signals(place, site, company, registry_status, flags, age)


def months(days: int) -> str:
    """Ancienneté en clair : « 12 jours », « 2 mois », « 3 ans »."""
    if days < 45:
        return f"{days} jour{'s' if days > 1 else ''}"
    if days < 730:
        return f"{round(days / 30.4)} mois"
    return f"{days // 365} ans"
