"""C132 : un secteur (BTP, mode, esthétique, sport…) regroupe tous ses métiers."""

import pytest

from prospection.domain.campaign_request import InvalidRequest, RawRequest, validate_request
from prospection.domain.criteria import Criteria
from prospection.domain.sectors import InvalidSectorFile, load_sectors, parse_sectors
from prospection.domain.trades import split_trades
from tests.storage.test_campaigns import LYON

GROUP = "- label: X\n  sectors:\n"


def _keywords(sector_id: str) -> tuple[str, ...]:
    return next(s for g in load_sectors() for s in g.sectors if s.id == sector_id).keywords


def test_C132_sectors_group_their_trades() -> None:
    assert "plombier" in _keywords("plombiers_electriciens")
    assert {"bijouterie", "boutique de vêtements", "boutique d'accessoires"} <= set(
        _keywords("mode")
    )
    assert {"salon de coiffure", "onglerie", "maquilleuse"} <= set(
        _keywords("esthetique") + _keywords("coiffure")
    )
    assert {"salle de sport", "coach sportif", "studio pilates", "studio yoga"} <= set(
        _keywords("sport")
    )


def test_C132_each_sector_fits_the_search_form() -> None:
    sectors = [s for g in load_sectors() for s in g.sectors]
    assert len({s.id for s in sectors}) == len(sectors)  # identifiants uniques
    assert all(1 <= len(s.keywords) <= 10 for s in sectors)  # 10 métiers au plus par recherche
    assert all("," not in k and k.strip() == k for s in sectors for k in s.keywords)


@pytest.mark.parametrize(
    "text",
    [
        "- label: X\n  sectors: []\n",
        GROUP + "    - {id: a, label: A, keywords: [a, b, c, d, e, f, g, h, i, j, k]}\n",
        GROUP + "    - {id: a, label: A, keywords: [a]}\n    - {id: a, label: B, keywords: [b]}\n",
        "pas une liste",
    ],
)
def test_C132_invalid_sector_file_refused(text: str) -> None:
    with pytest.raises(InvalidSectorFile):
        parse_sectors(text)


def test_C132_trades_split_on_commas_and_lines() -> None:
    assert split_trades("plombier\r\nélectricien,, ; maçon ") == [
        "plombier",
        "électricien",
        "maçon",
    ]


def test_C132_more_than_ten_trades_refused_not_cut() -> None:
    trades = [f"métier {n}" for n in range(11)]
    with pytest.raises(InvalidRequest) as refused:
        validate_request(RawRequest("Test", trades, [LYON], 10, Criteria(), False))
    assert refused.value.errors["trades"] == "10 métiers au plus : retirez-en."
