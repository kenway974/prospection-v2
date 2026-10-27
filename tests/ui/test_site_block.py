"""C52 : la fiche montre le bloc « Le site », textes du site neutralisés (règle 5)."""

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.domain.site_audit import Audit
from prospection.domain.site_report import SiteReport
from prospection.storage.schema_campaigns import prospects
from prospection.storage.site_codec import encode_site
from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE
from tests.ui.test_call_screens import client, text

__all__ = ["client"]  # fixture partagée


def test_C52_site_block_shown_and_escaped(client: TestClient, campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    page = text(client.get(f"/prospects/{pid}"))
    assert "Le site" in page and "Pas encore analysé." in page
    audit = Audit(40, ("<script>alert(1)</script>",), "Wix", False, False, False)
    report = SiteReport("fiche Google", "https://martin.fr", audit=audit)
    with campaign_db.begin() as conn:
        conn.execute(prospects.update().values(site_json=encode_site(report)))
    raw = client.get(f"/prospects/{pid}").text
    assert "40/100" in raw and "<script>alert(1)</script>" not in raw
    assert "&lt;script&gt;" in raw
