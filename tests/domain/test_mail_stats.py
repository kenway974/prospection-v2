"""C162, C164 : version la moins utilisée d'abord ; classement par taux de conversation."""

from prospection.domain.mail_stats import MIN_SENDS, SendResult, least_used, rank


def test_C162_least_used_version_first_then_file_order() -> None:
    assert least_used(["A", "B", "C"], {"A": 3, "B": 1, "C": 1}) == "B"
    assert least_used(["A", "B"], {}) == "A"


def results() -> list[SendResult]:
    winners = [SendResult({"objet": "A"}, True) for _ in range(4)]
    losers = [SendResult({"objet": "A"}, False) for _ in range(8)]
    others = [SendResult({"objet": "B"}, i < 1) for i in range(12)]
    few = [SendResult({"objet": "C"}, True) for _ in range(3)]
    return winners + losers + others + few


def test_C164_ranked_by_conversation_rate_with_counts() -> None:
    rows = rank(results(), "objet")
    assert [(r.label, r.sends, r.conversations) for r in rows] == [
        ("A", 12, 4), ("B", 12, 1), ("C", 3, 3),
    ]  # fmt: skip
    assert rows[0].rate == 33 and rows[0].enough
    assert not rows[2].enough and MIN_SENDS == 10  # 3 sur 3 : pas assez pour conclure


def test_C164_several_values_per_send_counted_each() -> None:
    sends = [SendResult({"points": ["no_https", "no_form"]}, True),
             SendResult({"points": ["no_https"]}, False)]  # fmt: skip
    rows = {r.label: (r.sends, r.conversations) for r in rank(sends, "points")}
    assert rows == {"no_https": (2, 1), "no_form": (1, 1)}
