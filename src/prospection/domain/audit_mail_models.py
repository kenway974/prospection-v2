"""Modèles des règles du mail d'audit (`data/mail_rules.yaml`) : point, secteur, accroche
(C145, C160, C172)."""

from typing import Literal

from pydantic import BaseModel, Field


class Point(BaseModel):
    titre: str = Field(min_length=1, max_length=80)
    poids: int = Field(ge=0, le=100)
    rang: Literal["legal", "clients", "suivi", "autre"]  # ordre des points du mail (C172)
    groupe: str | None = None
    probleme: str
    impact: str
    action: str


class Sector(BaseModel):
    mots: list[str] = Field(min_length=1)
    bonus: dict[str, int] = {}
    impacts: dict[str, str] = {}


class Condition(BaseModel):
    """Quand une accroche s'applique (C160) ; un critère absent ne compte pas."""

    note_min: float | None = None
    avis_min: int | None = None
    avec_site: bool | None = None
    age_max_mois: int | None = None
    age_min_ans: int | None = None
    label: str | None = None
    secteur: str | None = None


class Hook(BaseModel):
    quand: Condition
    texte: str
