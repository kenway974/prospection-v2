"""C137 : une page lourde (constructeur de pages) est lue jusqu'au formulaire en bas ; une page
coupée le dit."""

from prospection.sources.web_reader import MAX_BYTES, read_page
from tests.fake_http import fake_client
from tests.sources.test_web_reader import html

FORM = '<form><input type="email"></form>'


def test_C137_heavy_page_read_to_its_bottom_form() -> None:
    heavy = "<style>" + "x" * 900_000 + "</style>" + FORM
    client, _ = fake_client(lambda r: html(heavy))
    result = read_page(client, "https://site.fr")
    assert result.page is not None and FORM in result.page.html
    assert not result.page.truncated


def test_C137_cut_page_is_marked() -> None:
    client, _ = fake_client(lambda r: html("<p>" + "x" * (MAX_BYTES * 2) + "</p>"))
    result = read_page(client, "https://site.fr")
    assert result.page is not None and result.page.truncated
