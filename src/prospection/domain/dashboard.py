"""Indicateurs du tableau de bord (C80), sans division par zéro."""

import math


def qualification_rate(found: int, qualified: int) -> int | None:
    """Pourcentage de trouvés qui sont qualifiés ; None si rien trouvé."""
    return round(100 * qualified / found) if found else None


def cost_per_qualified(cost_cents: int, qualified: int) -> int | None:
    """Centimes par prospect qualifié, arrondis au-dessus ; None si aucun qualifié."""
    return math.ceil(cost_cents / qualified) if qualified else None
