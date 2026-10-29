"""C132 : un menu « Secteur » remplit les métiers, sur la recherche et sur le Terrain."""

import html

import pytest
from fastapi.testclient import TestClient

from prospection.ui.field_form import read_field_form
from tests.ui.test_call_screens import client

__all__ = ["client"]  # fixture partagée


@pytest.mark.parametrize("path", ["/recherche", "/terrain"])
def test_C132_sector_menu_fills_trades(client: TestClient, path: str) -> None:
    page = html.unescape(client.get(path).text)
    assert '<select id="secteur" data-remplit="metiers" aria-describedby="secteur-aide">' in page
    assert '<optgroup label="Sport">' in page
    assert 'data-metiers="salle de sport, coach sportif, studio pilates' in page
    assert "Sport, fitness, yoga, pilates" in page


def test_C132_field_search_keeps_all_trades_of_a_sector(client: TestClient) -> None:
    sport = (
        "salle de sport, coach sportif, studio pilates, studio yoga, crossfit, salle de musculation"
    )
    search, errors = read_field_form({"lat": "45.76", "lon": "4.83", "metiers": sport})
    assert not errors and search is not None and len(search.trades) == 6


def test_C132_synonyms_preview_reads_one_trade_per_line(client: TestClient) -> None:
    page = html.unescape(
        client.get("/recherche/synonymes", params={"metiers": "fleuriste\r\ncuisiniste"}).text
    )
    assert "fleuriste" in page and "cuisine sur mesure" in page
