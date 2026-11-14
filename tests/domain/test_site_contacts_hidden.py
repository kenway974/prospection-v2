"""C187 : adresses email déguisées reconnues, sans en inventer dans un texte ordinaire."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_contacts import find_contacts

SITE = "https://www.martin.fr/"


def _emails(text: str) -> tuple[str, ...]:
    return find_contacts(parse_page(f"<p>{text}</p>"), "FR", SITE).emails


def test_C187_common_disguises_are_read() -> None:
    for text in ("contact [at] martin [dot] fr", "contact(at)martin.fr",
                 "contact (arobase) martin (point) fr", "contact[@]martin.fr"):  # fmt: skip
        assert _emails(text) == ("contact@martin.fr",), text
    assert _emails("martin.coiffure (at) gmail (dot) com") == ("martin.coiffure@gmail.com",)


def test_C187_ordinary_text_gives_no_address() -> None:
    for text in (
        "Rendez-vous at home, dot com bubble, (at) vos côtés",
        "Réalisé par Studio @ agence.fr", "© 2024 Martin @ agence-web.fr",
        "Hébergé par OVH @ ovh.com", "Copyright 2024 @ webagence.fr",
        "Retrouvez-nous @ www.martin.fr", "Suivez-nous @ instagram.com",
        "Find us @ martin.fr", "Le 12/05 @ 14h.com", "Rendez-vous (at) home.fr",
        "Réalisation : Pixel (at) agencepixel (dot) fr",
    ):  # fmt: skip
        assert _emails(text) == (), text


def test_C187_no_address_cut_inside_a_word() -> None:
    assert _emails("notre équipe@jobs.martin.fr") == ()
