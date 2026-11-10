"""C171 : accroche choc tirée du premier point de l'audit, 10 mots au plus, en majuscules ;
sans phrase pour ce point, l'accroche tirée des faits (C160) reste."""

from datetime import date

import pytest

from prospection.domain.audit_mail_rules import (
    InvalidMailRules,
    hook_templates,
    load_mail_rules,
    parse_rules,
)
from prospection.domain.mail_hooks import LeadFacts, matching_hooks
from prospection.domain.mail_versions import MailVersions, decode_versions, encode_versions
from tests.domain.test_audit_mail import _raw

FACTS = LeadFacts("Martin Paysage", 4.8, 52, None, (), True, date(2026, 11, 10))


def test_C171_hook_points_the_first_problem_in_capitals() -> None:
    hooks = matching_hooks(FACTS, ("paysagiste",), first_point="no_legal_notice")
    assert hooks, "une accroche pour les mentions légales"
    for _, text in hooks:
        assert text == text.upper() and "MENTIONS LÉGALES" in text
        assert len(text.split()) <= 10


def test_C171_facts_hook_stays_without_audit_sentence() -> None:
    hooks = matching_hooks(FACTS, ("paysagiste",), first_point="gmb_no_hours")
    assert hooks[0][1].startswith("4,8 ★ sur 52 avis Google")


def test_C171_capitals_can_be_switched_off() -> None:
    hooks = {"no_https": ["Vos visiteurs voient « Non sécurisé »."]}
    rules = parse_rules({**_raw(), "accroche_majuscules": False, "accroches_audit": hooks})
    assert rules.accroche_majuscules is False


def test_C171_too_long_or_unknown_point_refused_at_start() -> None:
    long = " ".join(["mot"] * 11)
    with pytest.raises(InvalidMailRules, match="10 mots"):
        parse_rules({**_raw(), "accroches_audit": {"no_https": [long]}})
    with pytest.raises(InvalidMailRules, match="inconnu"):
        parse_rules({**_raw(), "accroches_audit": {"nope": ["Court."]}})


def test_C171_versions_keep_old_hook_codes_and_count_new_ones() -> None:
    rules = load_mail_rules()
    templates = hook_templates(rules)
    assert templates[: len(rules.accroches)] == [h.texte for h in rules.accroches]
    audit = rules.accroches_audit["no_legal_notice"][0]
    versions = MailVersions(rules.objets[0], audit, "courte")
    assert decode_versions(encode_versions(versions)) == versions


def test_C171_main_problems_all_have_a_hook() -> None:
    hooks = load_mail_rules().accroches_audit
    main = ("no_legal_notice", "no_privacy_policy", "no_form", "form_basic", "no_https")
    main += ("slow_mobile", "no_tracking", "no_mobile", "thin_content", "quote_incomplete")
    for code in main:
        assert hooks.get(code), code
