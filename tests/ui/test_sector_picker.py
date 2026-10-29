"""C132 : un menu « Secteur » remplit les métiers, sur la recherche et sur le Terrain."""

import html

import pytest
from fastapi.testclient import TestClient

from tests.ui.test_call_screens import client

__all__ = ["client"]  # fixture partagée


@pytest.mark.parametrize("path", ["/recherche", "/terrain"])
def test_C132_sector_menu_fills_trades(client: TestClient, path: str) -> None:
    page = html.unescape(client.get(path).text)
    assert '<select id="secteur" data-remplit="metiers">' in page
    assert '<optgroup label="Sport">' in page
    assert 'data-metiers="salle de sport, coach sportif, studio pilates' in page
    assert "Sport, fitness, yoga, pilates" in page
