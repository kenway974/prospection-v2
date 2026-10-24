"""C82 : limite d'essais de connexion."""

from datetime import UTC, datetime, timedelta

from prospection.domain.login_throttle import Throttle, check_login_allowed

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=UTC)


def minutes_ago(*minutes: int) -> list[datetime]:
    return [NOW - timedelta(minutes=m) for m in minutes]


def test_C82_four_recent_failures_still_allowed() -> None:
    assert check_login_allowed(minutes_ago(3, 2, 1, 0), NOW).allowed is True


def test_C82_five_failures_in_window_blocks_for_15_minutes() -> None:
    result = check_login_allowed(minutes_ago(4, 3, 2, 1, 0), NOW)
    assert result == Throttle(allowed=False, retry_after=timedelta(minutes=15))


def test_C82_block_ends_15_minutes_after_last_failure() -> None:
    failures = minutes_ago(4, 3, 2, 1, 0)
    assert check_login_allowed(failures, NOW + timedelta(minutes=15)).allowed is True


def test_C82_retry_after_rounds_up_to_the_minute() -> None:
    failures = minutes_ago(4, 3, 2, 1, 0)
    result = check_login_allowed(failures, NOW + timedelta(minutes=2, seconds=30))
    assert result == Throttle(allowed=False, retry_after=timedelta(minutes=13))


def test_C82_old_failures_do_not_count() -> None:
    assert check_login_allowed(minutes_ago(20, 19, 18, 17, 16), NOW).allowed is True


def test_C82_allowed_has_no_wait() -> None:
    assert check_login_allowed([], NOW) == Throttle(allowed=True, retry_after=timedelta(0))


def test_C82_failures_exactly_15_minutes_old_no_longer_block() -> None:
    assert check_login_allowed(minutes_ago(15, 15, 15, 15, 15), NOW).allowed is True
