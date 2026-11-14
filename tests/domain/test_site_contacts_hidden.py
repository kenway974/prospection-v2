"""C187 : adresses email déguisées reconnues, sans en inventer dans un texte ordinaire."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_contacts import find_contacts


def _emails(text: str) -> tuple[str, ...]:
    return find_contacts(parse_page(f"<p>{text}</p>"), "FR").emails


def test_C187_common_disguises_are_read() -> None:
    for text in ("contact [at] martin [dot] fr", "contact(at)martin.fr", "contact @ martin.fr",
                 "contact (arobase) martin (point) fr", "contact[@]martin.fr"):  # fmt: skip
        assert _emails(text) == ("contact@martin.fr",), text


def test_C187_ordinary_text_gives_no_address() -> None:
    assert _emails("Rendez-vous at home, dot com bubble, (at) vos côtés") == ()
