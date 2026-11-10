"""Travail de la tâche de fond entre deux campagnes : envois CRM, registre, compléments des
entreprises, nouveaux audits demandés, mises à jour, serveurs mail (C44, C53, C72, C76, C149,
C150, C156, C163, C169).

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
from prospection.application.mail_replies import check_replies
from prospection.application.registry_enrich import enrich_new_prospects
from prospection.application.site_reaudit import run_reaudits
from prospection.application.site_verdict import SiteChecker, skip_sites
from prospection.domain.google_cost import Pricing
from prospection.sources.gmail import GmailOAuth
from prospection.storage.secret_box import SecretBox

IDLE_PAUSE = timedelta(minutes=10)
REPLIES_PAUSE = timedelta(minutes=30)


class IdleWork:
    def __init__(
        self, engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing,
        now: Callable[[], datetime], mail_lookup: Callable[[str], str | None] | None,
        sites: SiteChecker = skip_sites, gmail: GmailOAuth | None = None,
        mail_queue: Callable[[], bool] | None = None,
    ) -> None:  # fmt: skip
        """`mail_queue` : envoie le prochain mail de la file s'il est temps (C169)."""
        self.engine, self.box, self.client, self.pricing = engine, box, client, pricing
        self.mail_queue = mail_queue
        self.now, self.mail_lookup, self.sites, self.gmail = now, mail_lookup, sites, gmail
        self.next_mail_check = self.next_details = datetime.min.replace(tzinfo=UTC)
        self.next_replies = self.next_details

    def run(self) -> bool:
        """Vrai si un travail a été fait."""
        if send_pending(self.engine, self.box, self.client, self.now()) > 0:
            return True
        if enrich_new_prospects(self.engine, self.client, self.now()) > 0:
            return True
        if run_reaudits(self.engine, self.sites, self.now()) > 0:  # C156 : à la demande
            return True
        if self.mail_queue and self.mail_queue():  # C169 : envoi groupé du mail d'audit
            return True
        if self.now() >= self.next_details:
            if detail_companies(self.engine, self.box, self.client, self.now()) > 0:
                return True
            self.next_details = self.now() + IDLE_PAUSE
        if self.gmail and self.now() >= self.next_replies:  # C163 : réponses au mail d'audit
            self.next_replies = self.now() + REPLIES_PAUSE
            if check_replies(self.engine, self.box, self.client, self.gmail, self.now()) > 0:
                return True
        if refresh_next(self.engine, self.box, self.client, self.pricing, self.now()):  # C76
            return True
        if self.mail_lookup is None or self.now() < self.next_mail_check:
            return False
        checked = check_mail_domains(self.engine, self.now(), self.mail_lookup)
        if not checked:
            self.next_mail_check = self.now() + IDLE_PAUSE
        return checked > 0
