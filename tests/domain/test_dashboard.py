"""C80 : taux de qualification et coût par prospect qualifié."""

from prospection.domain.dashboard import cost_per_qualified, qualification_rate


def test_C80_rates_never_divide_by_zero() -> None:
    assert qualification_rate(found=40, qualified=10) == 25
    assert qualification_rate(found=0, qualified=0) is None
    assert cost_per_qualified(cost_cents=350, qualified=10) == 35
    assert cost_per_qualified(cost_cents=100, qualified=3) == 34  # arrondi au centime supérieur
    assert cost_per_qualified(cost_cents=0, qualified=5) == 0
    assert cost_per_qualified(cost_cents=120, qualified=0) is None
