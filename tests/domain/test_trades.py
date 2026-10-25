"""C12 : métiers ; C15 : synonymes lancés automatiquement."""

from pathlib import Path

import pytest

from prospection.domain.trades import InvalidTradeFile, expand_queries, find_trade, load_trades

TRADES = load_trades()


def test_C15_cuisiniste_expands_to_cuisine_sur_mesure() -> None:
    queries = expand_queries(["Cuisinistes"], TRADES, synonyms_on=True)
    assert queries[0] == "Cuisinistes"
    assert "cuisine sur mesure" in queries
    assert len(queries) <= 3


def test_C15_synonyms_off_keeps_keyword_only() -> None:
    assert expand_queries(["cuisiniste"], TRADES, synonyms_on=False) == ["cuisiniste"]


def test_C15_unknown_trade_kept_as_is() -> None:
    assert expand_queries(["toiletteur canin"], TRADES, synonyms_on=True) == ["toiletteur canin"]


def test_C12_several_trades_without_duplicates() -> None:
    queries = expand_queries(["plombier", "Plomberie", "fleuriste"], TRADES, synonyms_on=True)
    assert queries.count("plombier") == 1
    assert any("fleur" in q for q in queries)
    assert len(queries) == len({q.casefold() for q in queries})


def test_find_trade_tolerates_accents_and_plural() -> None:
    trade = find_trade("Électriciens", TRADES)
    assert trade is not None and trade.id == "electricien"


def test_small_shops_are_known() -> None:
    for word in ["fleuriste", "boulangerie", "coiffeur", "esthéticienne", "garage"]:
        assert find_trade(word, TRADES) is not None, word


def test_trades_file_is_valid(tmp_path: Path) -> None:
    bad = tmp_path / "trades.yaml"
    bad.write_text("- id: x\n  label: X\n")
    with pytest.raises(InvalidTradeFile):
        load_trades(bad)
