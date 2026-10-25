"""C37 : la raison d'arrêt dit pourquoi et combien de prospects ont été trouvés."""

from prospection.domain.stop_reasons import budget_reached, exhausted, goal_reached


def test_C37_goal_reached_singular_and_plural() -> None:
    assert goal_reached(1) == "Objectif atteint : 1 prospect qualifié."
    assert goal_reached(20) == "Objectif atteint : 20 prospects qualifiés."


def test_C37_source_exhausted_says_how_many() -> None:
    assert exhausted(1, 5) == (
        "Plus de résultats sur Google Maps pour ces métiers et cette zone "
        "(1 qualifié sur 5 voulus)."
    )


def test_C37_C07_free_quota_and_paid_cap_are_told_apart() -> None:
    assert budget_reached(0, 3, 20) == (
        "Quota gratuit de Google atteint pour ce mois : 3 qualifiés sur 20 voulus, gardés. "
        "Pour continuer, relevez le plafond dans Réglages → Budget Google, "
        "ou attendez le 1er du mois."
    )
    assert budget_reached(550, 0, 20) == (
        "Plafond de 5,50 € atteint pour ce mois : 0 qualifié sur 20 voulus. "
        "Pour continuer, relevez le plafond dans Réglages → Budget Google, "
        "ou attendez le 1er du mois."
    )
