"""Les audits faits avant les codes (04/11/2026) retrouvent le code de chaque problème."""

from prospection.domain.site_codes import legacy_codes
from prospection.storage.site_codec import decode_site

OLD = ("Pas de HTTPS", "Chargement lent (4,2 s)", "Site pas mis à jour depuis 2019",
       "WordPress ancien (version 5.3), plus mis à jour", "Problème inconnu")  # fmt: skip


def test_old_problem_texts_get_their_code() -> None:
    assert legacy_codes(OLD) == ("no_https", "slow", "outdated", "old_wordpress", "")


def test_old_stored_audit_is_read_with_codes() -> None:
    audit = {"score": 50, "problems": list(OLD), "technology": None, "https": False,
             "mobile": True, "contact_form": True}  # fmt: skip
    report = decode_site({"origin": "fiche Google", "url": "http://a.fr", "audit": audit})
    assert report is not None and report.audit is not None
    assert report.audit.codes == legacy_codes(OLD) and report.audit.form_place is None
