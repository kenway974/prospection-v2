"""Vitesse mobile (PageSpeed) : note, problèmes en clair, site lent."""

from prospection.domain.page_speed import PageSpeed, is_slow, issue_labels, speed_line


def test_slow_site_and_plain_words() -> None:
    speed = PageSpeed(34, 6240, ("render-blocking-resources", "inconnu", "uses-optimized-images",
                                 "unused-javascript", "server-response-time"))  # fmt: skip
    assert is_slow(speed) and not is_slow(PageSpeed(90, 1200, ())) and not is_slow(None)
    assert issue_labels(speed) == [
        "Page bloquée par des fichiers à charger avant l'affichage", "Images trop lourdes",
        "Code JavaScript inutile",
    ]  # fmt: skip
    assert speed_line(speed) == "34/100 · contenu affiché en 6,2 s"
    assert speed_line(PageSpeed(80, None, ())) == "80/100"
