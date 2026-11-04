"""Travail de la tâche de fond entre deux campagnes : envois CRM, registre, compléments des
entreprises, mises à jour, serveurs mail (C44, C53, C72, C76, C149, C150).

Les compléments et les serveurs mail, quand il n'y a rien à faire (ou un service muet), ne
sont redemandés que 10 minutes plus tard : jamais d'appels en boucle.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.campaign_refresh import refresh_next
from prospection.application.company_details import detail_companies
from prospection.application.crm_export import send_pending
from prospection.application.mail_check import check_mail_domains
from prospection.application.registry_enrich import enrich_new_prospects
from prospection.domain.google_cost import Pricing
from prospection.storage.secret_box import SecretBox

IDLE_PAUSE = timedelta(minutes=10)


class IdleWork:
    def __init__(
        self, engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing,
        now: Callable[[], datetime], mail_lookup: Callable[[str], str | None] | None,
    ) -> None:  # fmt: skip
        self.engine, self.box, self.client, self.pricing = engine, box, client, pricing
        self.now, self.mail_lookup = now, mail_lookup
        self.next_mail_check = self.next_details = datetime.min.replace(tzinfo=UTC)

    def run(self) -> bool:
        """Vrai si un travail a été fait."""
        if send_pending(self.engine, self.box, self.client, self.now()) > 0:
            return True
        if enrich_new_prospects(self.engine, self.client, self.now()) > 0:
            return True
        if self.now() >= self.next_details:
            if detail_companies(self.engine, self.box, self.client, self.now()) > 0:
                return True
            self.next_details = self.now() + IDLE_PAUSE
        if refresh_next(self.engine, self.box, self.client, self.pricing, self.now()):  # C76
            return True
        if self.mail_lookup is None or self.now() < self.next_mail_check:
            return False
        checked = check_mail_domains(self.engine, self.now(), self.mail_lookup)
        if not checked:
            self.next_mail_check = self.now() + IDLE_PAUSE
        return checked > 0
