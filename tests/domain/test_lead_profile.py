"""C162 : profil du lead gardé à l'envoi (catégories lisibles, jamais de donnée personnelle)."""

from datetime import date

from prospection.domain.lead_profile import lead_profile

TODAY = date(2026, 11, 7)


def test_C162_profile_in_plain_categories() -> None:
    profile = lead_profile(("paysagiste",), "12 rue X, 69002 Lyon", True, 4.8, 52, 74,
                           date(2010, 1, 1), "basique (nom, email, message)", TODAY)  # fmt: skip
    assert profile == {
        "métier": "paysagiste", "ville": "Lyon", "site": "avec site", "note Google": "4,5 et plus",
        "avis Google": "50 et plus", "score": "70 et plus", "ancienneté": "plus de 10 ans",
        "formulaire": "basique (nom, email, message)",
    }  # fmt: skip


def test_C162_unknowns_said() -> None:
    profile = lead_profile((), "", False, None, 0, 20, None, None, TODAY)
    assert profile["note Google"] == "sans note" and profile["ancienneté"] == "inconnue"
    assert profile["site"] == "sans site" and profile["formulaire"] == "inconnu"
