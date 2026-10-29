"""Notifications : heures calmes, services autorisés, texte neutralisé."""

from datetime import datetime
from zoneinfo import ZoneInfo

from prospection.domain.push_rules import (
    allowed_endpoint,
    may_send,
    notification_text,
    quiet,
    safe_link,
)

PARIS = ZoneInfo("Europe/Paris")


def at(hour: int) -> datetime:
    return datetime(2026, 10, 29, hour, 30, tzinfo=PARIS)


def test_quiet_hours_from_21_to_8() -> None:
    assert quiet(at(22), 21, 8) and quiet(at(3), 21, 8) and quiet(at(7), 21, 8)
    assert not quiet(at(8), 21, 8) and not quiet(at(20), 21, 8)
    assert quiet(at(13), 12, 14) and not quiet(at(15), 12, 14)
    assert not quiet(at(3), 8, 8)  # désactivées


def test_follow_ups_go_through_quiet_hours_other_alerts_wait() -> None:
    assert may_send("relance", at(22), 21, 8)
    assert not may_send("nouveaux", at(22), 21, 8) and may_send("nouveaux", at(9), 21, 8)


def test_only_browser_push_services_are_called() -> None:
    assert allowed_endpoint("https://fcm.googleapis.com/fcm/send/abc")
    assert allowed_endpoint("https://updates.push.services.mozilla.com/wpush/v2/x")
    assert allowed_endpoint("https://web.push.apple.com/QGx")
    for bad in ("http://fcm.googleapis.com/x", "https://fcm.googleapis.com.evil.fr/x",
                "https://127.0.0.1/x", "https://fcm.googleapis.com:8443/x",
                "https://evilfcm.googleapis.com.attacker/x", "https://[::1/x"):  # fmt: skip
        assert not allowed_endpoint(bad), bad


def test_text_short_and_clean_link_internal_only() -> None:
    assert notification_text("Rappeler\x00 · Atelier\n · 14:30") == "Rappeler · Atelier · 14:30"
    assert len(notification_text("x" * 500)) == 180
    assert safe_link("/prospects/3") == "/prospects/3"
    assert safe_link("https://evil.fr") == "/" and safe_link("//evil.fr") == "/"
