"""Raisons d'arrêt d'une campagne, en clair (C37)."""

from prospection.domain.money import euros

NEXT_MONTH = (
    "Pour continuer, relevez le plafond dans Réglages → Budget Google, ou attendez le 1er du mois."
)


def _count(qualified: int, target: int) -> str:
    word = "qualifié" if qualified <= 1 else "qualifiés"
    return f"{qualified} {word} sur {target} voulus"


def goal_reached(qualified: int) -> str:
    words = "prospect qualifié" if qualified <= 1 else "prospects qualifiés"
    return f"Objectif atteint : {qualified} {words}."


def exhausted(qualified: int, target: int, registry_only: bool = False) -> str:
    what = "Plus d'entreprises récemment créées" if registry_only else (
        "Plus de résultats sur Google Maps"
    )  # fmt: skip
    return f"{what} pour ces métiers et cette zone ({_count(qualified, target)})."


def finished_with_skips(skipped: int, qualified: int, target: int) -> str:
    pages = "page ignorée" if skipped == 1 else "pages ignorées"
    return (
        f"Recherche finie avec {skipped} {pages} (service trop sollicité ou requête refusée) : "
        f"{_count(qualified, target)}. Relancez la même recherche plus tard, depuis un modèle."
    )


def budget_reached(budget_cents: int, qualified: int, target: int) -> str:
    what = (
        "Quota gratuit de Google atteint" if budget_cents == 0
        else f"Plafond de {euros(budget_cents)} atteint"
    )  # fmt: skip
    kept = ", gardés" if qualified else ""
    return f"{what} pour ce mois : {_count(qualified, target)}{kept}. {NEXT_MONTH}"
