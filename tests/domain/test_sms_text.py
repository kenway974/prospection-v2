"""C179 : textes des SMS dans un fichier modifiable ; chacun, une fois rempli, tient en un
seul SMS (alphabet SMS de base, place gardée pour la mention STOP)."""

import pytest

from prospection.domain.sms_text import (
    BUDGET,
    InvalidSmsRules,
    fill_sms,
    gsm_safe,
    load_sms_rules,
    parse_sms_rules,
)

LONG_NAME = "Société Générale des Travaux Paysagers et Jardins de l'Hérault Méditerranée"


def test_C179_three_versions_and_a_late_bounce_one() -> None:
    rules = load_sms_rules()
    assert set(rules.textes) == {"mail", "bloque", "sans_mail", "relance_bloque"}


def test_C179_every_filled_text_fits_one_sms() -> None:
    for kind in load_sms_rules().textes:
        text = fill_sms(kind, LONG_NAME, "Pas de mentions légales sur votre site", "06 81 78 73 25")
        assert len(text) <= BUDGET and gsm_safe(text), text
        assert "06 81 78 73 25" in text or kind == "mail"


def test_C179_names_outside_the_sms_alphabet_are_simplified() -> None:
    text = fill_sms("sans_mail", "Crêperie Côté Forêt", "Site lent", "06 81 78 73 25")
    assert "Creperie Coté Foret" in text and gsm_safe(text)  # é existe dans l'alphabet SMS


def test_C179_too_long_template_refused_at_start() -> None:
    kinds = ("mail", "bloque", "sans_mail", "relance_bloque")
    with pytest.raises(InvalidSmsRules, match="raccourcir"):
        parse_sms_rules({"textes": dict.fromkeys(kinds, "x" * 200)})
    with pytest.raises(InvalidSmsRules, match="inconnue"):
        parse_sms_rules({"textes": dict.fromkeys(kinds, "{nope}")})


def test_C179_app_refuses_to_start_with_broken_sms_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    import prospection.ui.app as app_module

    def broken() -> None:
        raise InvalidSmsRules("SMS « mail » trop long : à raccourcir (140 au plus).")

    monkeypatch.setattr(app_module, "load_sms_rules", broken)
    with pytest.raises(InvalidSmsRules):
        app_module.create_app(None, None)  # type: ignore[arg-type]
