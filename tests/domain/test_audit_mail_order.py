"""C172 : points rangés légal, clients perdus (référencement compris), suivi, le reste ; dans
un même rang, du plus lourd au plus léger."""

from prospection.domain.audit_mail import choose_points
from prospection.domain.audit_mail_rules import load_mail_rules


def test_C172_legal_comes_first_even_when_lighter() -> None:
    codes = ("no_tracking", "outdated", "no_https", "no_mobile", "no_legal_notice")
    points = choose_points(codes, ("boulangerie",))
    assert [p.code for p in points] == ["no_legal_notice", "no_https", "no_mobile"]


def test_C172_seo_is_lost_clients_and_tracking_before_the_rest() -> None:
    points = choose_points(("outdated", "no_tracking", "thin_content"), ())
    assert [p.code for p in points] == ["thin_content", "no_tracking", "outdated"]


def test_C172_every_point_has_a_rank() -> None:
    ranks = {code: point.rang for code, point in load_mail_rules().points.items()}
    assert set(ranks.values()) <= {"legal", "clients", "suivi", "autre"}
    assert ranks["no_cookie_consent"] == ranks["form_no_consent"] == "legal"
    assert ranks["low_authority"] == ranks["no_https"] == ranks["sim_sap"] == "clients"
    assert ranks["legacy_ga"] == "suivi" and ranks["outdated"] == "autre"
