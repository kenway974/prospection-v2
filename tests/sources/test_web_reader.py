"""C87, C88 : lecture d'une page de site, bornée et sans adresse interne."""

import httpx
import pytest

from prospection.sources.web_reader import MAX_BYTES, read_page
from tests.fake_http import fake_client

PAGE = "<html><head><title>Boulangerie Martin</title></head><body>Bonjour</body></html>"


def html(text: str = PAGE, status: int = 200, **headers: str) -> httpx.Response:
    return httpx.Response(status, text=text, headers={"Content-Type": "text/html", **headers})


def test_C88_page_read_with_final_address_and_time() -> None:
    client, _ = fake_client(lambda r: html())
    result = read_page(client, "https://boulangerie-martin.fr")
    assert result.page is not None and "Boulangerie Martin" in result.page.html
    assert result.page.url == "https://boulangerie-martin.fr" and result.page.seconds >= 0


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1/", "http://[::1]/", "http://localhost/", "http://intranet.local/",
     "ftp://site.fr/", "http://site.fr:8080/", "http://moi@site.fr/", "javascript:alert(1)", ""],
)  # fmt: skip
def test_C87_internal_or_odd_address_never_asked(url: str) -> None:
    client, recorder = fake_client(lambda r: html())
    result = read_page(client, url)
    assert result.page is None and result.problem and recorder.requests == []


def test_C87_each_redirection_is_checked() -> None:
    client, recorder = fake_client(
        lambda r: html("", 302, Location="http://169.254.169.254/latest/meta-data/")
    )
    result = read_page(client, "https://site.fr")
    assert result.page is None and len(recorder.requests) == 1


def test_C88_redirections_limited() -> None:
    client, recorder = fake_client(lambda r: html("", 301, Location="/encore"))
    assert read_page(client, "https://site.fr").page is None
    assert len(recorder.requests) == 4  # la page, puis 3 redirections au plus


def test_redirection_followed_to_the_final_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.scheme == "http":
            return html("", 301, Location="https://www.site.fr/")
        return html()

    client, _ = fake_client(handler)
    result = read_page(client, "http://site.fr")
    assert result.page is not None and result.page.url == "https://www.site.fr/"


def test_C88_size_limited() -> None:
    client, _ = fake_client(lambda r: html("<p>" + "x" * (MAX_BYTES * 3) + "</p>"))
    result = read_page(client, "https://site.fr")
    assert result.page is not None and len(result.page.html) <= MAX_BYTES


def test_C88_reading_stops_at_the_deadline() -> None:
    ticks = iter([0.0, 0.0, 100.0, 100.0, 100.0])
    client, _ = fake_client(lambda r: html())
    result = read_page(client, "https://site.fr", clock=lambda: next(ticks, 100.0))
    assert result.page is None and "trop lent" in (result.problem or "")


@pytest.mark.parametrize(
    ("reply", "problem"),
    [(html("x", 404), "erreur 404"), (html("%PDF", 200, **{"Content-Type": "application/pdf"}),
      "pas une page web")],
)  # fmt: skip
def test_error_or_non_html_said_plainly(reply: httpx.Response, problem: str) -> None:
    client, _ = fake_client(lambda r: reply)
    result = read_page(client, "https://site.fr")
    assert result.page is None and problem in (result.problem or "")


def test_unreachable_site_said_plainly() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("injoignable", request=request)

    client, _ = fake_client(down)
    assert read_page(client, "https://site.fr").problem == "Site injoignable"
