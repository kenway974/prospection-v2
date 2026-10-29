"""Origine des prospects : recherche sur Internet (à appeler) ou Terrain (C127, C128)."""

from dataclasses import dataclass

CALLS, FIELD = "appel", "terrain"
SOURCES = {CALLS: "À appeler", FIELD: "Terrain"}  # onglets de la liste, dans cet ordre


@dataclass(frozen=True)
class Scope:
    """Prospects listés : d'une origine, éventuellement d'une seule campagne."""

    source: str | None = None  # None : toutes les origines (export vers le CRM)
    campaign_id: int | None = None


ALL = Scope()
