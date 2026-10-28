"""C53 : la tâche de fond vérifie le serveur mail des emails trouvés ou saisis."""

from datetime import timedelta

from sqlalchemy import Engine

from prospection.application.mail_check import check_mail_domains
from prospection.domain.site_contacts import Contacts
from prospection.domain.site_report import SiteReport
from prospection.storage.mail_domains import mail_servers
from prospection.storage.schema_campaigns import prospects
from prospection.storage.site_codec import encode_site
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE


def with_emails(engine: Engine) -> None:
    [pid] = add(engine, PLACE)
    found = Contacts(("contact@martin.fr", "jean@Gmail.com"), (), ())
    site = SiteReport("fiche Google", "https://martin.fr", contacts=found)
    with engine.begin() as conn:
        conn.execute(prospects.update().where(prospects.c.id == pid).values(
            site_json=encode_site(site), contact_email="jean.martin@orange.fr"))  # fmt: skip


def test_C53_each_domain_checked_once(campaign_db: Engine) -> None:
    with_emails(campaign_db)
    asked: list[str] = []

    def lookup(domain: str) -> str | None:
        asked.append(domain)
        return "aucun" if domain == "martin.fr" else "mx"

    assert check_mail_domains(campaign_db, NOW, lookup) == 3
    assert sorted(asked) == ["gmail.com", "martin.fr", "orange.fr"]
    assert check_mail_domains(campaign_db, NOW, lookup) == 0  # déjà vérifiés
    with campaign_db.connect() as conn:
        known = mail_servers(conn, ["martin.fr", "gmail.com", "inconnu.fr"])
    assert known == {"martin.fr": "aucun", "gmail.com": "mx"}


def test_C53_silent_dns_retried_the_next_day_results_after_a_month(campaign_db: Engine) -> None:
    with_emails(campaign_db)
    check_mail_domains(campaign_db, NOW, lambda d: None if d == "martin.fr" else "mx")
    asked: list[str] = []

    def lookup(domain: str) -> str:
        asked.append(domain)
        return "mx"

    check_mail_domains(campaign_db, NOW + timedelta(hours=2), lookup)
    assert asked == []
    check_mail_domains(campaign_db, NOW + timedelta(days=2), lookup)
    assert asked == ["martin.fr"]
    asked.clear()
    check_mail_domains(campaign_db, NOW + timedelta(days=33), lookup)
    assert sorted(asked) == ["gmail.com", "martin.fr", "orange.fr"]
