"""C07 : jamais au-delà du plafond ; C16 : estimation du coût avant de lancer."""

from decimal import Decimal
from pathlib import Path

import pytest

from prospection.domain.google_cost import (
    Estimate,
    InvalidPricingFile,
    Pricing,
    call_cost_cents,
    can_call,
    estimate,
    load_pricing,
    pages_needed,
)

PRICING = Pricing(free_per_month=1000, usd_per_1000=Decimal("35"), eur_per_usd=Decimal("0.93"))


def test_C07_zero_budget_allows_free_quota_only() -> None:
    assert can_call(PRICING, calls_this_month=999, spent_cents=0, budget_cents=0) is True
    assert can_call(PRICING, calls_this_month=1000, spent_cents=0, budget_cents=0) is False


def test_call_cost_is_zero_inside_quota_then_rounded_up() -> None:
    assert call_cost_cents(PRICING, calls_this_month=10) == 0
    # 35 $ / 1000 * 0,93 = 3,255 centimes, arrondi à 4 centimes
    assert call_cost_cents(PRICING, calls_this_month=1000) == 4


def test_C07_budget_allows_paid_calls_until_spent() -> None:
    assert can_call(PRICING, calls_this_month=1500, spent_cents=496, budget_cents=500) is True
    assert can_call(PRICING, calls_this_month=1500, spent_cents=497, budget_cents=500) is False


def test_C16_estimate_zero_euros_inside_free_quota() -> None:
    result = estimate(PRICING, pages=27, calls_this_month=100, spent_cents=0, budget_cents=0)
    assert result == Estimate(pages=27, free_pages=27, paid_cents=0, fits=True)


def test_C16_estimate_beyond_quota() -> None:
    result = estimate(PRICING, pages=30, calls_this_month=990, spent_cents=0, budget_cents=0)
    assert result == Estimate(pages=30, free_pages=10, paid_cents=80, fits=False)


def test_pages_needed_is_the_maximum() -> None:
    assert pages_needed(queries=3, zones=2) == 18


def test_pricing_file_is_valid(tmp_path: Path) -> None:
    pricing = load_pricing()
    assert pricing.free_per_month == 1000
    bad = tmp_path / "pricing.yaml"
    bad.write_text("free_per_month: beaucoup\n")
    with pytest.raises(InvalidPricingFile):
        load_pricing(bad)
