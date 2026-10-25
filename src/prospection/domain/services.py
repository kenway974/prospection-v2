"""Services externes dont l'app utilise une clé."""

import enum


class Service(enum.Enum):
    GOOGLE = "google"
    NOTION = "notion"
    INSEE = "insee"

    @property
    def label(self) -> str:
        return {"google": "Google Maps", "notion": "Notion", "insee": "Sirène (INSEE)"}[self.value]
