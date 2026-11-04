"""Services externes dont l'app utilise une clé."""

import enum


class Service(enum.Enum):
    GOOGLE = "google"
    NOTION = "notion"
    INSEE = "insee"
    OPENPAGERANK = "openpagerank"

    @property
    def label(self) -> str:
        return {"google": "Google Maps", "notion": "Notion", "insee": "Sirène (INSEE)",
                "openpagerank": "Open PageRank"}[self.value]  # fmt: skip

    @property
    def help(self) -> str | None:
        """Où obtenir la clé, pour les services facultatifs."""
        return {
            "openpagerank": "Facultative : autorité des sites (0 à 10). Clé gratuite sur "
            "openpagerank.com (compte DomCop).",
        }.get(self.value)
