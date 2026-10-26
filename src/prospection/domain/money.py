"""Montants en euros, écrits à la française."""


def euros(cents: int) -> str:
    """Ex. 1250 → « 12,50 € », 0 → « 0 € »."""
    if cents % 100 == 0:
        return f"{cents // 100} €"
    return f"{cents // 100},{cents % 100:02d} €"
