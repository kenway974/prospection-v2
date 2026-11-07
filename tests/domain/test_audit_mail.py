"""C145 : mail d'audit court, par règles fixes, relié au business et adapté au métier."""

import pytest

from prospection.domain.audit_mail import STRUCTURES, MailSender, choose_points, draft_mail
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
    assert health[0].code == "no_privacy_policy" and "patients" in health[0].impact
    urgent = choose_points(("form_contact_only", "no_description"), ("plombier chauffagiste",))
    assert urgent[0].code == "form_contact_only" and "fuite" in urgent[0].impact


def test_C145_point_has_title_finding_cost_and_fix() -> None:
    point = choose_points(("no_https",), ())[0]
    assert point.title == "Un site marqué « Non sécurisé »"
    assert point.problem == "Votre site n'est pas en HTTPS."
    assert "entre 60 et 80 %" in point.impact and point.action.endswith("chez l'hébergeur.")


def test_C145_draft_is_short_with_portfolio_and_call() -> None:
    draft = draft_mail(choose_points(ALL, ()), "Boulangerie Martin", "martin.fr", SENDER)
    assert draft.subject == "Boulangerie Martin : audit express de votre site, 3 points à corriger"
    assert draft.body.startswith("Bonjour,\n\nJe suis Kenny Pignolet")
    assert "**1. Un site marqué « Non sécurisé »**\n- **Constat :** Votre site n'est pas" in (
        draft.body
    )
    assert "\n- **Impact :** " in draft.body
    assert "\n- **Solution :** " in draft.body and "\n\n**3. " in draft.body
    assert len(draft.body) < 1300  # C155 : concis
    assert "https://kenny.dev" in draft.body
    assert (
        "**Pour plus d'infos, appelez-moi au 06 12 34 56 78** : je vous explique tout, "
        "c'est gratuit et sans engagement." in draft.body
    )
    assert draft.body.rstrip().endswith("Bonne journée,\nKenny Pignolet")


def test_C145_calendly_link_when_set_and_singular_subject() -> None:
    sender = MailSender("Kenny", None, "https://kenny.dev", "https://calendly.com/kenny/15min")
    draft = draft_mail(choose_points(("no_https",), ()), "Martin", "martin.fr", sender)
    assert draft.subject == "Martin : audit express de votre site, 1 point à corriger"
    assert "Vous préférez choisir un créneau ? https://calendly.com/kenny/15min" in draft.body
    assert "répondez simplement à ce mail" in draft.body  # pas de téléphone réglé
    assert draft.body.rstrip().endswith("Kenny")


def test_C145_rules_file_is_valid_and_bad_rules_are_refused() -> None:
    assert "no_https" in load_mail_rules().points
    with pytest.raises(InvalidMailRules, match="inconnue"):
        parse_rules({**_raw(), "objets": ["{inconnue}"]})
    with pytest.raises(InvalidMailRules, match="secteur"):
        parse_rules({**_raw(), "secteurs": {"x": {"mots": ["a"], "bonus": {"nope": 1}}}})


def _raw() -> dict[str, object]:
    from importlib import resources

    import yaml

    text = resources.files("prospection.data").joinpath("mail_rules.yaml").read_text("utf-8")
    raw = yaml.safe_load(text)
    assert isinstance(raw, dict)
    return raw


def test_C160_hook_right_after_hello() -> None:
    hook = "4,8 ★ sur 52 avis Google : vos clients sont ravis, votre site doit le montrer."
    draft = draft_mail(choose_points(("no_https",), ()), "Martin", "martin.fr", SENDER, hook)
    assert draft.body.startswith(f"Bonjour,\n\n{hook}\n\nJe suis Kenny Pignolet")


def test_C161_no_site_intro_and_listing_points() -> None:
    points = choose_points(("no_site", "gmb_few_reviews", "gmb_no_hours"), ("paysagiste",))
    assert points[0].code == "no_site"
    draft = draft_mail(points, "Martin Paysage", "", SENDER)
    assert "la présence en ligne de Martin Paysage" in draft.body and "()" not in draft.body


def test_C160_company_name_with_braces_is_safe() -> None:
    hook = "Félicitations pour le lancement de {Martin} !"
    draft = draft_mail(choose_points(("no_https",), ()), "{Martin}", "m.fr", SENDER, hook)
    assert hook in draft.body


def test_C162_short_structure_and_chosen_subject() -> None:
    points = choose_points(("no_https",), ())
    draft = draft_mail(points, "Martin", "martin.fr", SENDER, subject=load_mail_rules().objets[1],
                       structure="courte")  # fmt: skip
    assert draft.subject != "Martin : audit express de votre site, 1 point à corriger"
    assert "Martin" in draft.subject
    assert "**1. Un site marqué « Non sécurisé »**\nLes navigateurs" in draft.body
    assert "Constat" not in draft.body
    assert STRUCTURES == ("détaillée", "courte")
