"""C82 : limite d'essais de connexion, par IP, avec un plafond global."""

from datetime import UTC, datetime, timedelta

from prospection.domain.login_throttle import Throttle, check_login_allowed

NOW = datetime(2026, 10, 24, 8, 0, tzinfo=UTC)
ALLOWED = Throttle(allowed=True, retry_after=timedelta(0))


def minutes_ago(*minutes: int) -> list[datetime]:
    return [NOW - timedelta(minutes=m) for m in minutes]


def test_C82_four_recent_failures_from_this_ip_still_allowed() -> None:
    failures = minutes_ago(3, 2, 1, 0)
    assert check_login_allowed(failures, failures, NOW) == ALLOWED


def test_C82_five_failures_from_this_ip_block_it_for_15_minutes() -> None:
    failures = minutes_ago(4, 3, 2, 1, 0)
    result = check_login_allowed(failures, failures, NOW)
    assert result == Throttle(allowed=False, retry_after=timedelta(minutes=15))


def test_C82_failures_from_other_ips_do_not_block_this_one() -> None:
    others = minutes_ago(4, 3, 2, 1, 0, 0, 0)
    assert check_login_allowed([], others, NOW) == ALLOWED


def test_C82_fifty_failures_from_all_ips_block_everyone() -> None:
    everyone = [NOW - timedelta(seconds=s) for s in range(50)]
    result = check_login_allowed([], everyone, NOW)
    assert result == Throttle(allowed=False, retry_after=timedelta(minutes=15))


def test_C82_forty_nine_failures_from_all_ips_still_allowed() -> None:
    everyone = [NOW - timedelta(seconds=s) for s in range(49)]
    assert check_login_allowed([], everyone, NOW) == ALLOWED


def test_C82_block_ends_15_minutes_after_last_failure() -> None:
    failures = minutes_ago(4, 3, 2, 1, 0)
    assert check_login_allowed(failures, failures, NOW + timedelta(minutes=15)) == ALLOWED


def test_C82_retry_after_rounds_up_to_the_minute() -> None:
    failures = minutes_ago(4, 3, 2, 1, 0)
    result = check_login_allowed(failures, failures, NOW + timedelta(minutes=2, seconds=30))
    assert result == Throttle(allowed=False, retry_after=timedelta(minutes=13))


def test_C82_old_failures_do_not_count() -> None:
    failures = minutes_ago(20, 19, 18, 17, 16)
    assert check_login_allowed(failures, failures, NOW) == ALLOWED


def test_C82_failures_exactly_15_minutes_old_no_longer_block() -> None:
    failures = minutes_ago(15, 15, 15, 15, 15)
    assert check_login_allowed(failures, failures, NOW) == ALLOWED
