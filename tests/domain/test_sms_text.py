"""C179 : textes des SMS dans un fichier modifiable ; chacun, une fois rempli, tient en un
seul SMS (alphabet SMS de base, place gardée pour la mention STOP), avec une phrase courte
par point de l'audit et jamais un nom coupé."""

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
KINDS = ("mail", "bloque", "sans_mail", "relance_bloque")


def test_C179_three_versions_and_a_late_bounce_one() -> None:
    assert set(load_sms_rules().textes) == set(KINDS)


def test_C179_every_filled_text_fits_one_sms_without_a_cut_name() -> None:
    for kind in KINDS:
        for point in [None, *load_sms_rules().problemes]:
            for name in ("Martin Paysage", LONG_NAME):
                text = fill_sms(kind, name, point, "06 81 78 73 25")
                assert len(text) <= BUDGET and gsm_safe(text), text
                assert text.startswith(("Bonjour Martin Paysage,", "Bonjour,")), text


def test_C179_short_phrase_of_the_first_point_never_absurd() -> None:
    text = fill_sms("sans_mail", "Boulangerie Dupont", "no_site", "06 81 78 73 25")
    assert "pas encore de site internet" in text and "sur votre site" not in text
    assert "quelques points simples" in fill_sms("mail", "Dupont", "sim_sap", "06")


def test_C179_names_outside_the_sms_alphabet_are_simplified() -> None:
    text = fill_sms("sans_mail", "Crêperie Côté Forêt", "slow", "06 81 78 73 25")
    assert "Creperie Coté Foret" in text and gsm_safe(text)  # é existe dans l'alphabet SMS


def test_C179_too_long_template_or_phrase_refused_at_start() -> None:
    with pytest.raises(InvalidSmsRules, match="raccourcir"):
        parse_sms_rules({"textes": dict.fromkeys(KINDS, "x" * 200)})
    with pytest.raises(InvalidSmsRules, match="inconnue"):
        parse_sms_rules({"textes": dict.fromkeys(KINDS, "{nope}")})
    with pytest.raises(InvalidSmsRules, match="raccourcir"):
        parse_sms_rules({"textes": dict.fromkeys(KINDS, "{probleme}"),
                         "problemes": {"no_form": "x" * 60}})  # fmt: skip


def test_C179_app_refuses_to_start_with_broken_sms_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    import prospection.ui.app as app_module

    def broken() -> None:
        raise InvalidSmsRules("SMS « mail » trop long : à raccourcir (140 au plus).")

    monkeypatch.setattr(app_module, "load_sms_rules", broken)
    with pytest.raises(InvalidSmsRules):
        app_module.create_app(None, None)  # type: ignore[arg-type]
