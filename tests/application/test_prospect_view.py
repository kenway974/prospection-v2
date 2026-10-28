"""C57 à C60 : score, raison, drapeaux et confiance sur la liste et la fiche."""

import dataclasses

from sqlalchemy import Engine

from prospection.application.prospect_card import card, prospect_list
from prospection.domain.site_contacts import Contacts
from prospection.domain.site_report import SiteReport
from prospection.storage.mail_domains import save_mail_server
from prospection.storage.schema_campaigns import prospects
from prospection.storage.site_codec import encode_site
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import PARIS, add
from tests.storage.test_campaigns import PLACE


def test_C57_C58_list_shows_score_and_reason(campaign_db: Engine) -> None:
    add(campaign_db, dataclasses.replace(PLACE, review_count=4))
    listing = prospect_list(campaign_db, None, "", "trouves", NOW)
    [row] = listing.rows
    summary = listing.summaries[row.id]
    assert summary.score == 75 and summary.reason == "sans site, 4 avis, mobile"


def test_C57_list_sorted_by_score(campaign_db: Engine) -> None:
    add(campaign_db, dataclasses.replace(PLACE, review_count=200),
        dataclasses.replace(PLACE, place_id="p2", name="Autre", review_count=2))  # fmt: skip
    names = [r.data["name"] for r in prospect_list(campaign_db, None, "", "score", NOW).rows]
    assert names == ["Autre", "Atelier"]


def test_C57_C60_card_explains_the_score_and_confidence(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, dataclasses.replace(PLACE, review_count=4))
    shown = card(campaign_db, pid, NOW, PARIS)
    seen = shown.insights
    assert seen is not None and seen.score == 75
    assert ("Très peu d'avis Google (4)", 20) in seen.score_details
    assert ("Téléphone", "+33612345678", "sûr") in seen.confidence


def test_C59_doubtful_email_flagged(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, PLACE)
    site = SiteReport("fiche Google", "https://atelier.fr",
                      contacts=Contacts(("contact@atelier.fr",), (), ()))  # fmt: skip
    with campaign_db.begin() as conn:
        conn.execute(prospects.update().values(site_json=encode_site(site)))
        save_mail_server(conn, "atelier.fr", "aucun", NOW)
    shown = card(campaign_db, pid, NOW, PARIS)
    seen = shown.insights
    assert seen is not None
    assert "Email contact@atelier.fr : le domaine n'a pas de serveur mail" in seen.flags
    assert ("contact@atelier.fr", "douteux", "le domaine n'a pas de serveur mail") in seen.emails


def test_C55_C56_phones_typed_and_leader_search_link(campaign_db: Engine) -> None:
    from prospection.storage.company_codec import encode_company
    from tests.domain.test_company import LYON_SAS

    [pid] = add(campaign_db, PLACE)
    site = SiteReport("fiche Google", "https://atelier.fr",
                      contacts=Contacts((), ("+33478123456", "+33612345678"), ()))  # fmt: skip
    with campaign_db.begin() as conn:
        conn.execute(prospects.update().values(
            site_json=encode_site(site), company_json=encode_company(LYON_SAS),
            registry_status="sûr"))  # fmt: skip
    seen = card(campaign_db, pid, NOW, PARIS).insights
    assert seen is not None
    assert seen.phones == [("06 12 34 56 78", "mobile", "fiche Google"),
                           ("04 78 12 34 56", "fixe", "site")]  # fmt: skip
    assert "keywords=Marie+DUPONT+Atelier" in seen.linkedin


def test_C110_C112_card_prepares_the_call(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, dataclasses.replace(PLACE, review_count=4))
    seen = card(campaign_db, pid, NOW, PARIS).insights
    assert seen is not None and seen.sheet.hook is not None and "Atelier" in seen.sheet.hook
    assert seen.sheet.notice.startswith("Indices à confirmer")
    assert ("Avis", "4 avis (rythme non disponible)") in seen.health


def test_C56_unsure_company_leader_never_searched(campaign_db: Engine) -> None:
    from prospection.storage.company_codec import encode_company
    from tests.domain.test_company import LYON_SAS

    [pid] = add(campaign_db, PLACE)
    with campaign_db.begin() as conn:
        conn.execute(prospects.update().values(
            company_json=encode_company(LYON_SAS), registry_status="à confirmer"))  # fmt: skip
    seen = card(campaign_db, pid, NOW, PARIS).insights
    assert seen is not None and "DUPONT" not in seen.linkedin and "g%C3%A9rant" in seen.linkedin
