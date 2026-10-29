"""PageSpeed Insights : réponse validée, mesures gardées, erreurs triées (faux serveur)."""

import httpx
import pytest

from prospection.sources.page_speed import SpeedBusy, SpeedRefused, page_speed
from tests.fake_http import fake_client, json_reply, timeout

ANSWER = {"lighthouseResult": {
    "categories": {"performance": {"score": 0.34}},
    "audits": {
        "largest-contentful-paint": {"score": 0.1, "numericValue": 6240.4},
        "uses-optimized-images": {"score": 0.4, "details": {"overallSavingsMs": 900}},
        "render-blocking-resources": {"score": 0.2, "details": {"overallSavingsMs": 2100}},
        "unused-css-rules": {"score": 0.95},
        "audit-inconnu": {"score": 0},
    },
}}  # fmt: skip


def test_mobile_score_display_time_and_main_issues() -> None:
    client, seen = fake_client(json_reply(200, ANSWER))
    speed = page_speed(client, "AIza-test", "https://boulangerie.fr")
    assert speed is not None and speed.score == 34 and speed.display_ms == 6240
    assert speed.issues == ("render-blocking-resources", "uses-optimized-images")
    params = seen.requests[0].url.params
    assert params["strategy"] == "mobile" and params["url"] == "https://boulangerie.fr"


def test_errors_sorted() -> None:
    url = "https://boulangerie.fr"
    assert page_speed(fake_client(json_reply(400, {}))[0], "k", url) is None  # site illisible
    assert page_speed(fake_client(json_reply(200, {"autre": 1}))[0], "k", url) is None
    for busy in (json_reply(429, {}), json_reply(503, {}), timeout,
                 lambda r: httpx.Response(200, text="pas du json")):  # fmt: skip
        with pytest.raises(SpeedBusy):
            page_speed(fake_client(busy)[0], "k", url)
    with pytest.raises(SpeedRefused, match="PageSpeed Insights API"):
        page_speed(fake_client(json_reply(403, {}))[0], "k", url)
