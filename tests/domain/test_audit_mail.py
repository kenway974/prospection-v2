"""C145 : mail d'audit court, par règles fixes, relié au business et adapté au métier."""

import pytest

from prospection.domain.audit_mail import MailSender, choose_points, draft_mail
from prospection.domain.audit_mail_rules import InvalidMailRules, load_mail_rules, parse_rules

SENDER = MailSender("Kenny Pignolet", "06 12 34 56 78", "https://kenny.dev", None)
ALL = ("no_social", "no_https", "no_description", "no_mobile", "no_legal_notice", "slow")


def test_C145_three_points_at_most_strongest_first() -> None:
    points = choose_points(ALL, ("boulangerie",))
    assert [p.code for p in points] == ["no_https", "no_mobile", "slow"]


def test_C145_same_group_never_twice_and_unknown_codes_ignored() -> None:
    points = choose_points(("slow", "slow_mobile", "no_social", ""), ())
    assert [p.code for p in points] == ["slow_mobile"]


def test_C145_trade_changes_order_and_wording() -> None:
    codes = ("no_mobile", "no_privacy_policy", "no_legal_notice", "phone_not_clickable")
    health = choose_points(codes, ("osteopathe",))
    assert health[0].code == "no_privacy_policy" and "patients" in health[0].text
    urgent = choose_points(("form_contact_only", "no_description"), ("plombier chauffagiste",))
    assert urgent[0].code == "form_contact_only" and "fuite" in urgent[0].text


def test_C145_point_reads_problem_then_business_then_action() -> None:
    point = choose_points(("no_https",), ())[0]
    assert point.text.startswith("Votre site n'est pas sécurisé (pas de HTTPS).")
    assert "entre 60 et 80 %" in point.text and point.text.endswith("règle le problème.")


def test_C145_draft_is_short_with_portfolio_and_call() -> None:
    draft = draft_mail(choose_points(ALL, ()), "Boulangerie Martin", "martin.fr", SENDER)
    assert draft.subject == "Boulangerie Martin : 3 points à améliorer sur votre site"
    assert draft.body.startswith("Bonjour,\n\nJe suis Kenny Pignolet")
    assert "1. Votre site n'est pas sécurisé" in draft.body and "\n\n3. " in draft.body
    assert "https://kenny.dev" in draft.body and "appel de 15 minutes" in draft.body
    assert "répondez simplement" in draft.body
    assert draft.body.rstrip().endswith("Kenny Pignolet\n06 12 34 56 78")


def test_C145_calendly_link_when_set_and_singular_subject() -> None:
    sender = MailSender("Kenny", None, "https://kenny.dev", "https://calendly.com/kenny/15min")
    draft = draft_mail(choose_points(("no_https",), ()), "Martin", "martin.fr", sender)
    assert draft.subject == "Martin : 1 point à améliorer sur votre site"
    assert "https://calendly.com/kenny/15min" in draft.body
    assert draft.body.rstrip().endswith("Kenny")


def test_C145_rules_file_is_valid_and_bad_rules_are_refused() -> None:
    assert "no_https" in load_mail_rules().points
    with pytest.raises(InvalidMailRules, match="inconnue"):
        parse_rules({**_raw(), "objet": "{inconnue}"})
    with pytest.raises(InvalidMailRules, match="secteur"):
        parse_rules({**_raw(), "secteurs": {"x": {"mots": ["a"], "bonus": {"nope": 1}}}})


def _raw() -> dict[str, object]:
    from importlib import resources

    import yaml

    text = resources.files("prospection.data").joinpath("mail_rules.yaml").read_text("utf-8")
    raw = yaml.safe_load(text)
    assert isinstance(raw, dict)
    return raw
