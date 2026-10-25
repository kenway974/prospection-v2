"""CRM de destination (C05) : Notion, ou aucun (export fichier seulement, C09)."""

import enum


class Crm(enum.Enum):
    NONE = "none"
    NOTION = "notion"
